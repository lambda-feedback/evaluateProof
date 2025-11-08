import json
from typing import Dict, List, Tuple, TypedDict
import os
from dotenv import load_dotenv
from openai import OpenAI

openai_api_key_var = "OPENAI_API_KEY"

class MathTutor:
    def __init__(self, config_path: str, env_path: str = '.env', model=None):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        if model is not None:
            self.config['model_name'] = model
        self._load_environment(env_path)
        self.client = OpenAI(api_key=os.getenv(openai_api_key_var))
        self.tokens_processed = 0
        self.tokens_emitted = 0
        # At initialization, we verify that the config directives contain the necessary keys
        # if not all(key in self.config['directives'] for key in ['feedback', 'correctness']):
        #    raise ValueError("Config directives must contain keys 'feedback' and 'correctness'")

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return json.load(f)

    def _load_environment(self, env_path: str):
        load_dotenv(env_path)
        required_env_vars = [openai_api_key_var]
        for var in required_env_vars:
            if not os.getenv(var):
                raise ValueError(f"Missing required environment variable: {var}")
            
    def get_num_tokens(self):
        return self.tokens_processed, self.tokens_emitted

    def process_input(self, submission: str, exemplary_solution: str, temperature: float = 0.0, model: str = None) -> Tuple[str, str]:
        """
        process_input takes a submission (question and associated answer) and an exemplary solution (can be "No exemplary solution provided") and returns feedback and assessed correctness.
        :param question: The question to be answered.
        :param submission: The student's submission, which includes the question and the answer.
        :param exemplary_solution: The exemplary solution to the question.
        :param temperature: The temperature parameter for the LLM that checks the solution.
        :return: A tuple containing the feedback and correctness of the submission.
        """
        print(f"Exemplary solution: {exemplary_solution}")
        print(f"Submission: {submission}")

        workflow_override = None
        
        try:
            # try to parse the exemplary solution as a json string
            exemplary_solution_data = json.loads(exemplary_solution)
            question = exemplary_solution_data["question"]
            exemplary_solution = exemplary_solution_data["answer"]
            answer = submission
            
            # Check if there's a workflow field to override the default directives
            if "workflow" in exemplary_solution_data:
                workflow_path = exemplary_solution_data["workflow"]
                # complete path to absolute path
                workflow_full_path = workflow_path
                print(f"Loading workflow from: {workflow_full_path}")
                with open(workflow_full_path, 'r') as f:
                    workflow_config = json.load(f)
                    workflow_override = workflow_config.get('directives')
                    
        except ValueError:
            # in this case, we assume that the exemplary solution is a string that contains just the exemplary answer, or maybe nothing (i.e. `No exemplary solution provided`)
            # In this case, we try to split the submission into question and answer
            split_submission = submission.split("Answer:")
            print(f"Split submission: {split_submission}")
            if len(split_submission) > 1:
                question = split_submission[0]
                answer = "Answer:".join(split_submission[1:])
            else:
                # If we can't split the submission, treat the entire submission as the question
                # and set exemplary_solution to indicate none was provided
                question = submission
                answer = submission
                exemplary_solution = "No exemplary solution provided"
        # Check submission length
        # if len(submission) > 5000:
        #    return "I apologize, but your submission is too long. Please limit your submission to 5000 characters or less.", "incorrect"

        # Call OpenAI moderation endpoint with omni-moderation-latest model
        moderation_response = self.client.moderations.create(
            model="omni-moderation-latest",
            input=submission
        )
        if moderation_response.results[0].flagged:
            return "I apologize, but I cannot process this submission as it contains content that has been flagged as inappropriate. Please revise your submission and try again.", "incorrect"

        # Check if it's a mathematical question using gpt-4-mini
        math_check_submission = f"Question: {question}\nSubmission: {submission}"
        print(f"Checking submission for math content...: {submission}")
        math_check_response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a classifier that determines if a given text contains a statement that contains mathematical content. Respond only with 'Yes' or 'No'."},
                {"role": "user", "content": math_check_submission}
            ],
            temperature=0.0
        )
        math_check_response = math_check_response.choices[0].message.content.strip().lower()
        print(f"Math check response: {math_check_response}")
        is_math_question = math_check_response == 'yes'
        if not is_math_question:
            return f"I'm sorry, but your submission doesn't appear to contain a mathematical question. Could you please rephrase your question to focus on a mathematical topic? Here is the submission:{submission}", "incorrect"

        # Update token counts
        # self.tokens_processed += math_check_response.usage.total_tokens
        # self.tokens_processed += moderation_response.usage.total_tokens
        assignment_data = (question, answer, exemplary_solution)
        # Use workflow override if specified, otherwise use default config directives
        directives = workflow_override if workflow_override is not None else self.config['directives']
        _, state = self._process_directives(assignment_data, directives, temperature, model)

        return state['feedback']

    def _get_assignment_data(self, text: str) -> str:
        return f"{self.config['context_instructions']}{text}"

    def _process_directives(self, assignment_data: Tuple[str, str, str], directives: Dict, temperature: float, model: str = None) -> Tuple[str, Dict]:
        if model and "__testmode__" in model:
            model, evaluator = model.split("__testmode__")
        else:
            evaluator = None
        state = {
            "prompt": assignment_data[0],
            "output": assignment_data[1],
            "solution": assignment_data[2]
        }
        print(f"State: {state}")
        state.update(self.config.get('variables', {}))

        print(f"Directives steps: {directives.keys()}")
        print(f"Number of directives: {len(directives.items())}")

        for key, directive in directives.items():
            if key == 'auto_solution' and state['solution'] != "No exemplary solution provided":
                state[key] = state['solution']
                continue
            if isinstance(directive, str):
                try:
                    prompt = directive.format(**state)
                except Exception as e:
                    print(f"Error formatting directive: {e}")
                    raise e
                response = self._get_completion(prompt, temperature, model)
                state[key] = response
            # print(f"State after step {key}: {state}")
            # We print the prompt and response for debugging purposes
            # print(f"Prompt: {prompt}")
            #print(f"Response: {response}")
            print(f"Step being run: {key}")
        # print(f"Correctness: {state['correctness']}")
        if evaluator:
            evaluator_prompt = f"Here is a mathematical homework assignment and the solution submitted by a student:\n\n{state['prompt']}\n\n{state['output']}\n\nHere is feedback given by a teaching assistant:\n\n{state['feedback']}\n\nPlease perform a meta-evaluation of the feedback given to the student. Highlight errors, weaknesses, and strengths of the feedback provided."
            evaluator_response = self.client.chat.completions.create(
                model=evaluator,
                messages =[
                    {"role": "user", "content": evaluator_prompt}
                ]
            )
            meta_feedback = evaluator_response.choices[0].message.content
            state['feedback'] = state['feedback'] + "\n\nMeta-evaluation of the feedback:\n\n" + meta_feedback
        return state['feedback'], state

    def _get_completion(self, prompt: str, temperature: float, model: str = None) -> str:
        sys_message = self.config['context_instructions']
        resolved_model = model if model is not None else self.config.get('model_name', 'gpt-5-mini')
        
        # Check if this is a reasoning model (o1, o3, o4, gpt-5 series)
        is_reasoning_model = any(reasoning_prefix in resolved_model for reasoning_prefix in ['o1', 'o3', 'o4', 'gpt-5'])
        
        if is_reasoning_model:
            # Reasoning models don't support system messages
            response = self.client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                reasoning_effort="low"
            )
        else:
            response = self.client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": sys_message},
                    {"role": "user", "content": prompt}
                ],
            temperature=temperature
        )
        self.tokens_processed += response.usage.prompt_tokens
        self.tokens_emitted += response.usage.completion_tokens
        return response.choices[0].message.content

    def process_batch(self, data: List[Dict], temperature: float = 0.0) -> List[Tuple[str, str]]:
        return [self.process_input(item['prompt'], item['output'], temperature) for item in data]

# Example usage:
# def main():
#     config = MathTutorConfig(model_name="gpt-4")
#     tutor = MathTutor(config, 'path_to_config.json')
#     result = tutor.process_input("What is 2+2?", "The answer is 4.")
#     print(result)
#
# if __name__ == "__main__":
#     main()
