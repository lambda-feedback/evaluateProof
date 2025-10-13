import unittest
import openai
import os
import dotenv

dotenv.load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    from .evaluation import evaluation_function, Params
except ImportError:
    from evaluation import evaluation_function, Params

class TestEvaluationFunction(unittest.TestCase):
    """
    TestCase Class used to test the algorithm.
    ---
    Tests are used here to check that the algorithm written
    is working as it should.

    It's best practise to write these tests first to get a
    kind of 'specification' for how your algorithm should
    work, and you should run these tests before committing
    your code to AWS.

    Read the docs on how to use unittest here:
    https://docs.python.org/3/library/unittest.html

    Use evaluation_function() to check your algorithm works
    as it should.
    """

    def setUp(self):
        self.params = Params({'model_name': 'gpt-4o-mini'})

    def correctness_test(self, result):
        """
        This is a helper function for the test that checks if, given the output of the evaluation function, the submission is correct or not.
        """
        result_str = result['feedback']
        prompt_correctness = f"Given this feedback on a mathematical homework submission, is it reasonable to call the submission correct overall? Answer `yes` if it is, `no` otherwise:\n\n{result_str}"
        response_correctness = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_correctness}],
            temperature=0
        )
        return "yes" in response_correctness.choices[0].message.content.lower()

    def test_correct_submission(self):
        submission = "What is 2+2?#Answer: The answer is 4."
        exemplary_solution = "Question: What is 2+2? Answer: The answer is 4."
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertTrue(self.correctness_test(result))

    def test_correct_submission_json_exemplary(self):
        submission = "The answer is 4."
        exemplary_solution = '{"question": "What is 2+2?", "answer": "The answer is 4."}'

        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertTrue(self.correctness_test(result))


    def test_incorrect_submission(self):
        submission = "What is 2+2?#Answer: The answer is 5."
        exemplary_solution = "Question: What is 2+2? Answer: The answer is 4."
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertFalse(self.correctness_test(result))

    def test_no_exemplary_solution_correct(self):
        submission = "What is 2+2?#Answer: The answer is 4."
        exemplary_solution = "No exemplary solution provided"
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        print(result)
        self.assertTrue(self.correctness_test(result))

    def test_no_exemplary_solution_incorrect(self):
        submission = "What is 2+2?#Answer: The answer is 3."
        exemplary_solution = "No exemplary solution provided"
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertFalse(self.correctness_test(result))

if __name__ == "__main__":
    unittest.main()