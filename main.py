import argparse
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from functions.call_function import available_functions, call_function
from prompts import system_prompt


def main():
    parser = argparse.ArgumentParser(description="AI Code Assistant")
    parser.add_argument("user_prompt", type=str, help="Prompt to send to Gemini")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")

    client = genai.Client(api_key=api_key)
    messages = [types.Content(role="user", parts=[types.Part(text=args.user_prompt)])]
    if args.verbose:
        print(f"User prompt: {args.user_prompt}\n")

    generate_content(client, messages, args.verbose)


def generate_content(client, messages, verbose, max_turns=20):
    for turn in range(max_turns):
        if verbose:
            print(f"\n=== Turn {turn + 1} ===")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                tools=[available_functions],
                system_instruction=system_prompt,
            ),
        )

        if not response.candidates:
            raise RuntimeError("Model returned no candidates")

        candidate = response.candidates[0]
        model_content = candidate.content

        messages.append(model_content)

        if not response.function_calls:
            for part in model_content.parts:
                if part.text:
                    print(part.text)
            return

        for function_call in response.function_calls:
            tool_result = call_function(function_call, verbose)

            if (
                not tool_result.parts
                or not tool_result.parts[0].function_response
                or not tool_result.parts[0].function_response.response
            ):
                raise RuntimeError(
                    f"Empty function response for {function_call.name}"
                )

            messages.append(
                types.Content(
                    role="tool",
                    parts=[tool_result.parts[0]],
                )
            )

    print("Reached maximum number of turns (20)")


if __name__ == "__main__":
    main()