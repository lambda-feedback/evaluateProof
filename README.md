# evaluateProof

An AWS Lambda evaluation function for the [LambdaFeedback](https://lambdafeedback.com) platform that uses OpenAI's GPT models to provide automated feedback on undergraduate mathematics submissions.

The function implements a two-stage LLM pipeline:
1. **Mark scheme generation** — produces a 0–5 rubric specific to the question.
2. **Feedback generation** — uses that rubric to give the student concise, actionable feedback.

## Table of Contents
- [Repository Structure](#repository-structure)
- [How It Works](#how-it-works)
  - [Two-Stage Evaluation Pipeline](#two-stage-evaluation-pipeline)
  - [Custom Workflows](#custom-workflows)
  - [Submission Limits](#submission-limits)
  - [Docker & AWS](#docker--aws)
  - [GitHub Actions](#github-actions)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Test / Debug Mode](#test--debug-mode)
- [Pre-requisites](#pre-requisites)

## Repository Structure

```
app/
    evaluation.py           # Entry point — delegates to MathTutor
    math_tutor.py           # Two-stage LLM evaluation logic (OpenAI)
    preview.py              # Preview function (returns response as-is)
    config_tutor.json       # Production LLM directives
    config_tutor_test.json  # Test LLM directives (loaded first on startup)
    evaluation_tests.py     # Unit tests for evaluation_function
    preview_tests.py        # Unit tests for preview_function
    requirements.txt        # Python dependencies
    Dockerfile              # Builds the deployable image
    docs/
        dev.md              # Developer-facing documentation
        user.md             # Student/teacher-facing documentation
    test_configs/           # Per-question workflow configs used in tests

.github/
    workflows/
        test-and-deploy.yml # CI: lint → test → deploy staging → deploy production

config.json                 # Declares the function name: "evaluateProof"
```

## How It Works

### Two-Stage Evaluation Pipeline

When a student submits an answer, `evaluation_function` in `evaluation.py` calls `MathTutor.process_input`, which runs two sequential LLM calls:

1. **Markscheme directive** (`config_tutor.json → directives.markscheme`): the model receives the question and generates a 0–5 marking rubric.
2. **Feedback directive** (`config_tutor.json → directives.feedback`): the model receives the question, the student's solution, and the rubric, then returns feedback. The numeric grade is intentionally withheld to avoid misinterpretation.

The `answer` field passed from the platform is expected to be a JSON string:

```json
{
  "question": "Prove that ...",
  "answer": "An exemplary solution ...",
  "workflow": "/app/app/test_configs/config0.json"
}
```

If no exemplary solution is available, the function falls back gracefully.

### Custom Workflows

The `answer` field may include a `"workflow"` key pointing to a JSON config file. This lets different questions use different LLM directive chains without redeploying the function. Workflow configs follow the same `{ "directives": { ... } }` schema as `config_tutor.json`.

### Submission Limits

The function enforces a cap of **6 submissions per student per response area**. Once reached, further submissions return a message asking the student to contact their instructor. The current count is provided via `params.submission_context.submissions_per_student_per_response_area` and is displayed in the feedback prefix on each submission.

### Docker & AWS

The function is packaged as a Docker image and deployed to AWS Lambda via Amazon ECR. It extends the shared [BaseEvaluationFunctionLayer](https://github.com/lambda-feedback/BaseEvalutionFunctionLayer) image, which provides the request/response middleware and handler wiring.

### GitHub Actions

Pushes to `main` trigger `.github/workflows/test-and-deploy.yml`:

1. **Test** — lint with `flake8`, run `evaluation_tests.py` and `preview_tests.py` (requires `OPENAI_API_KEY` secret).
2. **Deploy Staging** — build and push image to the staging ECR repository, then call the backend `grading-function/ensure` route.
3. **Deploy Production** — same as staging but against the production ECR repository and API.

## Getting Started

1. Clone this repository.
2. Ensure the following secrets are set in your GitHub repository settings:
   - `OPENAI_API_KEY` — used by the evaluation pipeline and tests.
   - `LAMBDA_CONTAINER_PIPELINE_AWS_ID` / `LAMBDA_CONTAINER_PIPELINE_AWS_SECRET` — AWS credentials for ECR.
   - `FUNCTION_ADMIN_API_KEY` — LambdaFeedback backend API key.
3. Edit `app/evaluation.py` and `app/math_tutor.py` to change evaluation behaviour.
4. Update the LLM prompts in `app/config_tutor.json` to tune the mark scheme and feedback directives.
5. Add or update tests in `app/evaluation_tests.py`.
6. Push to `main` — the CI/CD pipeline handles the rest.

To run tests locally:

```bash
cd app
pip install -r requirements.txt pytest
OPENAI_API_KEY=sk-... pytest -v evaluation_tests.py preview_tests.py
```

## Configuration

| File | Purpose |
| --- | --- |
| `config.json` | Sets `EvaluationFunctionName` to `"evaluateProof"` — used by CI to tag the Docker image. |
| `app/config_tutor.json` | Production LLM directive chain (markscheme → feedback). |
| `app/config_tutor_test.json` | Loaded first on Lambda cold-start; falls back to `config_tutor.json` if missing. |
| `app/test_configs/` | Per-question workflow overrides referenced from the `answer` JSON. |

## Test / Debug Mode

Prefixing a response with `[[test_mode_temporary]]` activates debug mode, bypassing the normal evaluation flow. Supported commands:

| Command | Behaviour |
| --- | --- |
| `[[test_mode_temporary]] [feedback] <hex>` | Decodes a hex-encoded string and returns it as feedback. |
| `[[test_mode_temporary]] [sleep <n>]` | Sleeps for `n` seconds, then returns a confirmation message. |
| `[[test_mode_temporary]] [tree] [<depth>]` | Returns a directory tree of the app, up to `depth` levels (default 3). |
| `[[test_mode_temporary]] [full trace] <response>` | Runs the normal pipeline and returns the full internal state as JSON. |

## Pre-requisites

- Python 3.8+
- An OpenAI API key with access to GPT-4 (or the model specified in your config).
- Docker (for local image builds).
- `git` or GitHub Desktop.
- A code editor such as VS Code.