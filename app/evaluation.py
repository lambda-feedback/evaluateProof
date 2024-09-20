from logging import error

from sys import exit

from typing import Any, TypedDict

from .math_tutor import MathTutor

try:
    tutor = MathTutor('config_tutor.json')
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

class Result(TypedDict):
    is_correct: bool
    feedback: str

def evaluation_function(response: Any, answer: Any, params: Params) -> Result:
    """
    Function used to evaluate a student response.
    ---
    The handler function passes three arguments to evaluation_function():

    - `response` which are the answers provided by the student.
    - `answer` which are the correct answers to compare against. Normally, we won't have those in our application.
    - `params` which are any extra parameters that may be useful,
        e.g., error tolerances.

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
    
    # We assume that response in our case contains the student's answer as well as the question
    # We don't assume that we get an exemplary answer, but if `answer` is a string, we provide it to the tutor

    assert isinstance(response, str)
    
    if not isinstance(answer, str):
        answer = f"No exemplary solution provided"
    
    try:
        feedback, correctness = tutor.process_input(response, answer)
    except Exception as e:
        feedback = f"An error occurred during the evaluation: {e}"
        correctness = False

    correctness = (correctness.lower() == "correct")

    return Result(is_correct=correctness, feedback=feedback)


