# evaluateProof

An AWS Lambda evaluation function for the [LambdaFeedback](https://lambdafeedback.com) platform that uses OpenAI's GPT models to provide automated feedback on undergraduate mathematics submissions.

The function implements a two-stage LLM pipeline:
1. **Mark scheme generation** — produces a 0–5 rubric specific to the question.
2. **Feedback generation** — uses that rubric to give the student concise, actionable feedback.

## Deployment
[![Create Release Request](https://img.shields.io/badge/Create%20Release%20Request-blue?style=for-the-badge)](https://github.com/lambda-feedback/evaluateProof/issues/new?template=release-request.yml)

## Table of Contents
- [Deployment](#deployment)
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
        test-lint.yml             # PRs: flake8 lint
        staging-deploy.yml        # Push to main (or manual): lint → deploy to staging
        production-deploy.yml     # Manual: deploy to production with a version bump
        pre_production_tests.yml  # Manual: database tests against staging (not used here, LLM-backed)
    ISSUE_TEMPLATE/
        release-request.yml       # Form for requesting a production release

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

The function is packaged as a Docker image and deployed to AWS Lambda. It extends the shared [BaseEvaluationFunctionLayer](https://github.com/lambda-feedback/BaseEvalutionFunctionLayer) image (`main-3.12`, Python 3.12), which provides the request/response middleware and handler wiring. The deployed function reads `OPENAI_API_KEY` from its environment.

### GitHub Actions

The workflows call the shared [evaluation-function-workflows](https://github.com/lambda-feedback/evaluation-function-workflows) `deploy.yml`:

1. **Pull requests** (`test-lint.yml`): install dependencies and lint with `flake8`. The unit tests are not run in CI because they call the OpenAI API.
2. **Staging** (`staging-deploy.yml`): runs on every push to `main`, or manually via *Run workflow*. It lints, then builds the image and deploys it to staging. To try a branch on staging before merging, run it manually and select that branch.
3. **Production** (`production-deploy.yml`): run manually, choosing a patch/minor/major version bump. Use the **Create Release Request** button above to request a release. Database tests are disabled for this function because it is LLM-backed.

## Getting Started

1. Clone this repository.
2. Edit `app/evaluation.py` and `app/math_tutor.py` to change evaluation behaviour.
3. Update the LLM prompts in `app/config_tutor.json` to tune the mark scheme and feedback directives.
4. Add or update tests in `app/evaluation_tests.py`, and run them locally (see below), since CI does not.
5. Open a pull request. Optionally deploy the branch to staging (see [GitHub Actions](#github-actions)) and test it there.
6. Merge to `main` to deploy to staging, then request a production release.

The deploy secrets (`LAMBDA_CONTAINER_PIPELINE_AWS_ID`/`_SECRET`, `FUNCTION_ADMIN_API_KEY_STAGING`/`_PRODUCTION`, `GCP_DEPLOY`) are provided at the organisation level.

To run tests locally (requires an OpenAI API key):

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

- Python 3.12+
- An OpenAI API key with access to GPT-4 (or the model specified in your config).
- Docker (for local image builds).
- `git` or GitHub Desktop.
- A code editor such as VS Code.