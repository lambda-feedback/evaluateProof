import json
from typing import Dict, List, Tuple, TypedDict
import os
from dotenv import load_dotenv
from openai import OpenAI

openai_api_key_var = "OPENAI_API_KEY"

class MathTutor:
    def __init__(self, config_path: str, env_path: str = '.env', model=None):
        self.config = self._load_config(config_path)
        if model is not None:
            self.config['model_name'] = model
        self._load_environment(env_path)
        self.client = OpenAI(api_key=os.getenv(openai_api_key_var))
        # At initialization, we verify that the config directives contain the necessary keys
        if not all(key in self.config['directives'] for key in ['feedback', 'correctness']):
            raise ValueError("Config directives must contain keys 'feedback' and 'correctness'")

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return json.load(f)

    def _load_environment(self, env_path: str):
        load_dotenv(env_path)
        required_env_vars = [openai_api_key_var]
        for var in required_env_vars:
            if not os.getenv(var):
                raise ValueError(f"Missing required environment variable: {var}")

    def process_input(self, submission: str, exemplary_solution: str, temperature: float = 0.0, model: str = None) -> Tuple[str, str]:
        """
        process_input takes a submission (question and associated answer) and an exemplary solution (can be "No exemplary solution provided") and returns feedback and assessed correctness.
        :param submission: The student's submission, which includes the question and the answer.
        :param exemplary_solution: The exemplary solution to the question.
        :param temperature: The temperature parameter for the LLM that checks the solution.
        :return: A tuple containing the feedback and correctness of the submission.
        """
        try:
            question, answer = submission.split("#Answer:")
        except ValueError:
            raise ValueError("Submission must contain the question and the answer separated by '#Answer:'")
        assignment_data = (question, answer, exemplary_solution)
        _, state = self._process_directives(assignment_data, self.config['directives'], temperature, model)
        return state['feedback'], state['correctness']

    def _get_assignment_data(self, text: str) -> str:
        return f"{self.config['context_instructions']}{text}"

    def _process_directives(self, assignment_data: Tuple[str, str], directives: Dict, temperature: float, model: str = None) -> Tuple[str, Dict]:
        state = {
            "prompt": assignment_data[0],
            "output": assignment_data[1],
            "solution": assignment_data[2]
        }
        state.update(self.config.get('variables', {}))

        print(f"Directives steps: {directives.keys()}")
        print(f"Number of directives: {len(directives.items())}")

        for key, directive in directives.items():
            if key == 'auto_solution' and state['solution'] != "No exemplary solution provided":
                state[key] = state['solution']
                continue
            if directive is not None:
                try:
                    prompt = directive.format(**state)
                except Exception as e:
                    print(f"Error formatting directive: {e}")
                    raise e
                # print(f"Prompt: {prompt}")
                response = self._get_completion(prompt, temperature, model)
                state[key] = response
            # print(f"State after step {key}: {state}")
            # We print the prompt and response for debugging purposes
            # print(f"Prompt: {prompt}")
            #print(f"Response: {response}")
            print(f"Step being run: {key}")
        print(f"Correctness: {state['correctness']}")
            # print(f"Directive being run: {directive}")
        return state['feedback'], state

    def _get_completion(self, prompt: str, temperature: float, model: str = None) -> str:
        sys_message = self.config['context_instructions']
        response = self.client.chat.completions.create(
            model = model if model is not None else self.config.get('model_name', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": sys_message},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
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
