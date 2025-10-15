from logging import error

from typing import Any, TypedDict

from .math_tutor import MathTutor

from time import sleep

import json
import os

max_retries = 4

# Get the directory of the current file to build relative paths
current_dir = os.path.dirname(os.path.abspath(__file__))
config_test_path = os.path.join(current_dir, 'config_tutor_test.json')
config_path = os.path.join(current_dir, 'config_tutor.json')

tutor = None
try:
    tutor = MathTutor(config_test_path)
except Exception as e:
    error(f"An error occurred during the initialization of the tutor: {e}")
    for _ in range(max_retries):
        sleep(1)
        try:
            tutor = MathTutor(config_path)
            break
        except Exception as e:
            error(f"An error occurred during the initialization of the tutor: {e}")
    if tutor is None:
        error(f"Failed to initialize MathTutor with either config file")
        
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
        
        # this is an ugly hack to circumvent the standard logic for testing purposes
        if "[[test_mode_temporary]]" in response:
            # Remove the test mode marker
            response = response.replace("[[test_mode_temporary]]", "").strip()
            
            # [feedback] HEX_ENCODED_STRING - decode and return the hex-encoded string
            if response.startswith("[feedback]"):
                hex_string = response[len("[feedback]"):].strip()
                try:
                    # Decode hex-encoded bytestring to regular string
                    decoded_bytes = bytes.fromhex(hex_string)
                    decoded_string = decoded_bytes.decode('utf-8')
                    return Result(feedback=decoded_string, is_correct=False)
                except (ValueError, UnicodeDecodeError) as e:
                    return Result(feedback=f"Error decoding hex string: {e}", is_correct=False)
            
            # [sleep n] - sleep for n seconds before returning a response
            if response.startswith("[sleep"):
                try:
                    # Extract the number of seconds to sleep
                    parts = response.split()
                    if len(parts) >= 2:
                        sleep_seconds = float(parts[1].rstrip(']'))
                        sleep(sleep_seconds)
                        return Result(feedback=f"Slept for {sleep_seconds} seconds", is_correct=False)
                    else:
                        return Result(feedback="Invalid [sleep n] format. Use: [sleep n] where n is a number", is_correct=False)
                except (ValueError, IndexError) as e:
                    return Result(feedback=f"Error parsing sleep command: {e}", is_correct=False)
            
            # [full trace] RESPONSE - process normally but return full state trace as JSON
            if response.startswith("[full trace]"):
                actual_response = response[len("[full trace]"):].strip()
                
                # Process the response normally through the tutor
                if not isinstance(answer, str):
                    answer_str = f"No exemplary solution provided"
                else:
                    answer_str = answer
                
                try:
                    # We need to access the internal state from the tutor
                    # Parse the response to extract question and answer
                    try:
                        json_answer = json.loads(answer_str)
                        question = json_answer["question"]
                        solution = json_answer["answer"]
                    except ValueError:
                        # Split the submission into question and answer
                        split_submission = actual_response.split("Answer:")
                        if len(split_submission) > 1:
                            question = split_submission[0]
                            answer_part = "Answer:".join(split_submission[1:])
                        else:
                            question = actual_response
                            answer_part = actual_response
                        solution = "No exemplary solution provided"
                    
                    # Get the full state by calling the internal method
                    assignment_data = (question, answer_part if 'answer_part' in locals() else actual_response, solution)
                    _, state = tutor._process_directives(assignment_data, tutor.config['directives'], 0.0, params.get('model_name'))
                    
                    # Convert the full state to JSON string and return
                    full_trace_json = json.dumps(state, indent=2, ensure_ascii=False)
                    return Result(feedback=full_trace_json, is_correct=False)
                except Exception as e:
                    return Result(feedback=f"Error processing full trace: {e}", is_correct=False)
            
            # If no recognized test command, return error
            return Result(feedback="Unknown test mode command", is_correct=False)


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
    
    except Exception as e:
        return Result(feedback=f"Unexpected error during evaluation: {e}", is_correct=False)


