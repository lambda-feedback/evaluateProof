import unittest

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

    def test_invalid_submission_format(self):
        submission = "This is not a valid submission format"
        exemplary_solution = "Some solution"
        
        with self.assertRaises(ValueError):
            evaluation_function(submission, exemplary_solution, self.params)

    def test_correct_submission(self):
        submission = "What is 2+2?#Answer: The answer is 4."
        exemplary_solution = "The answer is 4."
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertTrue(result['is_correct'])

    def test_incorrect_submission(self):
        submission = "What is 2+2?#Answer: The answer is 5."
        exemplary_solution = "The answer is 4."
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertFalse(result['is_correct'])

    def test_no_exemplary_solution_correct(self):
        submission = "What is 2+2?#Answer: The answer is 4."
        exemplary_solution = "No exemplary solution provided"
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertTrue(result['is_correct'])

    def test_no_exemplary_solution_incorrect(self):
        submission = "What is 2+2?#Answer: The answer is 3."
        exemplary_solution = "No exemplary solution provided"
        
        result = evaluation_function(submission, exemplary_solution, self.params)
        self.assertFalse(result['is_correct'])

if __name__ == "__main__":
    unittest.main()