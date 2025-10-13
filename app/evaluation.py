import logging
import time
from typing import Any, TypedDict, Optional

from .math_tutor import MathTutor

import json

# Set up logging
logger = logging.getLogger(__name__)

# Global tutor instance (initialized lazily)
_tutor: Optional[MathTutor] = None
_tutor_init_error: Optional[str] = None


def _get_tutor() -> MathTutor:
    """
    Lazy initialization of the MathTutor instance.
    Tries multiple config paths with retries and caches the result.
    Raises RuntimeError if initialization fails after all attempts.
    """
    global _tutor, _tutor_init_error
    
    # Return cached tutor if already initialized
    if _tutor is not None:
        return _tutor
    
    # Return cached error if already failed
    if _tutor_init_error is not None:
        raise RuntimeError(_tutor_init_error)
    
    # Configuration paths to try
    config_paths = ['app/config_tutor_test.json', 'config_tutor.json', 'config_tutor_test.json']
    max_retries = 3  # Total attempts per config
    retry_delay = 1  # Seconds between retries
    
    all_errors = []
    
    for config_path in config_paths:
        for attempt in range(max_retries):
            try:
                attempt_info = f"attempt {attempt + 1}/{max_retries}" if max_retries > 1 else "single attempt"
                logger.info(f"Attempting to initialize MathTutor with config: {config_path} ({attempt_info})")
                _tutor = MathTutor(config_path)
                logger.info(f"Successfully initialized MathTutor with config: {config_path}")
                return _tutor
                
            except FileNotFoundError as e:
                error_msg = f"Config file not found: {config_path}"
                logger.warning(error_msg)
                all_errors.append(error_msg)
                # Don't retry if file doesn't exist
                break
                
            except ValueError as e:
                error_msg = f"Configuration error with {config_path} (attempt {attempt + 1}): {str(e)}"
                logger.warning(error_msg)
                all_errors.append(error_msg)
                
                # Retry if we have attempts left
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    break
                    
            except Exception as e:
                error_msg = f"Failed to initialize with {config_path} (attempt {attempt + 1}): {str(e)}"
                logger.warning(error_msg)
                all_errors.append(error_msg)
                
                # Retry if we have attempts left
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    break
    
    # All initialization attempts failed
    _tutor_init_error = "Failed to initialize MathTutor after all retry attempts. Errors: " + "; ".join(all_errors)
    logger.error(_tutor_init_error)
    raise RuntimeError(_tutor_init_error)
        
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
    try:
        feedback_prefix = ""

        # get the number of submissions per student per response area
        try:
            submissions_per_student_per_response_area = params['submission_context']['submissions_per_student_per_response_area']
            if submissions_per_student_per_response_area >= max_submissions_per_student_per_response_area:
                feedback = f"You have reached the maximum number of submissions per student for this question. Please try another one. If you believe this is an error, please contact your instructor."
                return Result(is_correct=False, feedback=feedback)
            else:
                feedback_prefix = f"You have submitted {submissions_per_student_per_response_area+1} times. You have {max_submissions_per_student_per_response_area - submissions_per_student_per_response_area - 1} submissions remaining.\n\n"

        except KeyError:
            # for the moment, pass in case this is not provided; otherwise we break test cases
            pass
        
        # We assume that response in our case contains the student's answer as well as the question
        # We don't assume that we get an exemplary answer, but if `answer` is a string, we provide it to the tutor

        # Validate response is a string instead of using assert
        if not isinstance(response, str):
            return Result(feedback="Invalid response format: expected string", is_correct=False)
        
        if not isinstance(answer, str):
            answer = f"No exemplary solution provided"
        else:
            try:
                # we expect `answer` to be a json string containing the question and an exemplary solution
                json_answer = json.loads(answer)
                # If it's valid JSON, keep the original answer string
                # The MathTutor will parse it again
            except (ValueError, json.JSONDecodeError):
                # Not JSON - could be a plain string exemplary solution or "No exemplary solution provided"
                # Leave answer as is - MathTutor will handle it
                pass
        
        # Get the tutor instance (may raise RuntimeError for initialization failures)
        # RuntimeError is allowed to propagate - the platform will handle it
        tutor = _get_tutor()
        
        # Try to process the input
        try:
            feedback = tutor.process_input(response, answer, model=params['model_name'])
        except ValueError as e:
            # Input validation error from MathTutor - return as feedback
            logger.warning(f"Input validation error: {e}")
            feedback = f"Unable to process your submission: {str(e)}"

        feedback = feedback_prefix + feedback
        return Result(feedback=feedback, is_correct=False)
    
    except RuntimeError:
        # Initialization errors - let them propagate to the platform
        raise
    except Exception as e:
        # Unexpected errors during evaluation - return as feedback
        logger.exception(f"Unexpected error during evaluation: {e}")
        return Result(feedback=f"Unexpected error during evaluation: {e}", is_correct=False)


