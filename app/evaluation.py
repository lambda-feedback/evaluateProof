from logging import error

from sys import exit

from typing import Any, TypedDict

from .math_tutor import MathTutor

import json

try:
    tutor = MathTutor('config_tutor_test.json')
except Exception as e:
    error(f"An error occurred during the initialization of the tutor: {e}")
    try:
        tutor = MathTutor('app/config_tutor.json')
    except Exception as e:
        error(f"An error occurred during the initialization of the tutor: {e}")
        # exit with suitable error code
        exit(1)
        
class Params(TypedDict):
    model_name: str
    submission_context: dict

class Result(TypedDict):
    feedback: str
    is_correct: bool

max_submissions_per_student_per_response_area = 6

def evaluation_function(response: Any, answer: Any, params: Params) -> Result:
    """
    Function used to evaluate a student response.
    ---
    The handler function passes three arguments to evaluation_function():

    - `response` which are the answers provided by the student.
    - `answer` which are the correct answers to compare against. Normally, we won't have those in our application.
    - `params` which are any extra parameters that may be useful,
        e.g., error tolerances.

    The `params` dictionary now includes a 'submission_context' key with the following structure:
    {
        'submission_context': {
            'submissions_per_student_per_response_area': int
        }
    }
    This can be used to limit student usage or provide feedback based on the number of submissions.

    The output of this function is what is returned as the API response
    and therefore must be JSON-encodable. It must also conform to the
    response schema.

    Any standard python library may be used, as well as any package
    available on pip (provided it is added to requirements.txt).

    The way you wish to structure you code (all in this function, or
    split into many) is entirely up to you. All that matters are the
    return types and that evaluation_function() is the main function used
    to output the evaluation response.
    """
    feedback_prefix = ""

    # get the number of submissions per student per response area
    try:
        submissions_per_student_per_response_area = params['submission_context']['submissions_per_student_per_response_area']
        if submissions_per_student_per_response_area >= max_submissions_per_student_per_response_area:
            feedback = f"You have reached the maximum number of submissions per student per response area. Please contact the administrator if you believe this is an error."
            correctness = "incorrect"
            return Result(is_correct=correctness, feedback=feedback)
        else:
            feedback_prefix = f"You have submitted {submissions_per_student_per_response_area+1} times. You have {max_submissions_per_student_per_response_area - submissions_per_student_per_response_area - 1} submissions remaining.\n\n"

    except KeyError:
        # for the moment, pass in case this is not provided; otherwise we break test cases
        pass
    
    # We assume that response in our case contains the student's answer as well as the question
    # We don't assume that we get an exemplary answer, but if `answer` is a string, we provide it to the tutor

    assert isinstance(response, str)
    
    if not isinstance(answer, str):
        answer = f"No exemplary solution provided"
    else:
        try:
            # we expect `answer` to be a json string containing the question and an exemplary solution
            json_answer = json.loads(answer)
            question = json_answer["question"]
            solution = json_answer["answer"]
        except ValueError:
            answer = f"No exemplary solution provided"
    
    try:
        feedback = tutor.process_input(response, answer, model=params['model_name'])
    except Exception as e:
        feedback = f"An error occurred during the evaluation: {e}"

    feedback = feedback_prefix + feedback
    return Result(feedback=feedback, is_correct=False)


