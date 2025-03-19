import json
import os
import anthropic
import datetime
import configparser

# Configuration handling
CONFIG_FILE = "config.ini"
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"
DEFAULT_MAX_TOKENS = 64000
DEFAULT_THINKING_BUDGET = 20000
DEFAULT_TEMPERATURE = 1.0

# Global variables
config = None
streaming_mode = True

# Directory setup
CONVERSATIONS_DIR = "conversations"
SYSTEM_PROMPTS_DIR = "system_prompts"
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
os.makedirs(SYSTEM_PROMPTS_DIR, exist_ok=True)


def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        # First-time setup
        config["API"] = {
            "key": input("Enter your Claude API key: "),
            "model": DEFAULT_MODEL
        }
        config["Parameters"] = {
            "temperature": str(DEFAULT_TEMPERATURE),
            "max_tokens": str(DEFAULT_MAX_TOKENS),
            "thinking_budget": str(DEFAULT_THINKING_BUDGET)
        }
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    return config


# System prompt management
def list_system_prompts():
    files = [f for f in os.listdir(SYSTEM_PROMPTS_DIR) if f.endswith('.txt')]
    return sorted(files)


def create_system_prompt():
    name = input("Enter a name for the system prompt: ")
    filename = f"{name}.txt" if not name.endswith('.txt') else name
    filepath = os.path.join(SYSTEM_PROMPTS_DIR, filename)

    print("\nEnter your system prompt (type 'DONE' on a new line when finished):")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == 'DONE':
            break
        lines.append(line)

    prompt_text = "\n".join(lines)

    with open(filepath, 'w') as f:
        f.write(prompt_text)

    print(f"System prompt saved as '{filename}'")
    return filename


def view_system_prompt(filename):
    filepath = os.path.join(SYSTEM_PROMPTS_DIR, filename)
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        print(f"\n===== {filename} =====")
        print(content)
        print("=" * 20)
    except FileNotFoundError:
        print(f"System prompt file '{filename}' not found.")


def edit_system_prompt(filename):
    filepath = os.path.join(SYSTEM_PROMPTS_DIR, filename)
    try:
        with open(filepath, 'r') as f:
            current_content = f.read()

        print(f"\nCurrent content of '{filename}':")
        print(current_content)
        print("\nEnter new content (type 'DONE' on a new line when finished):")

        lines = []
        while True:
            line = input()
            if line.strip().upper() == 'DONE':
                break
            lines.append(line)

        new_content = "\n".join(lines)

        with open(filepath, 'w') as f:
            f.write(new_content)

        print(f"System prompt '{filename}' has been updated.")
    except FileNotFoundError:
        print(f"System prompt file '{filename}' not found.")


def delete_system_prompt(filename):
    filepath = os.path.join(SYSTEM_PROMPTS_DIR, filename)
    try:
        os.remove(filepath)
        print(f"System prompt '{filename}' has been deleted.")
    except FileNotFoundError:
        print(f"System prompt file '{filename}' not found.")


def manage_system_prompts():
    while True:
        print("\n===== System Prompts Management =====")
        print("1. Create new system prompt")

        prompts = list_system_prompts()
        if prompts:
            print("2. View system prompt")
            print("3. Edit system prompt")
            print("4. Delete system prompt")

            print("\nAvailable system prompts:")
            for i, name in enumerate(prompts):
                print(f"   {i + 1}. {name}")

        print("0. Back to main menu")

        choice = input("\nEnter your choice: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            create_system_prompt()
        elif choice == '2' and prompts:
            try:
                idx = int(input("Enter the number of the prompt to view: ")) - 1
                if 0 <= idx < len(prompts):
                    view_system_prompt(prompts[idx])
                else:
                    print("Invalid prompt number.")
            except ValueError:
                print("Please enter a valid number.")
        elif choice == '3' and prompts:
            try:
                idx = int(input("Enter the number of the prompt to edit: ")) - 1
                if 0 <= idx < len(prompts):
                    edit_system_prompt(prompts[idx])
                else:
                    print("Invalid prompt number.")
            except ValueError:
                print("Please enter a valid number.")
        elif choice == '4' and prompts:
            try:
                idx = int(input("Enter the number of the prompt to delete: ")) - 1
                if 0 <= idx < len(prompts):
                    confirm = input(f"Are you sure you want to delete '{prompts[idx]}'? (y/n): ").lower()
                    if confirm == 'y':
                        delete_system_prompt(prompts[idx])
                else:
                    print("Invalid prompt number.")
            except ValueError:
                print("Please enter a valid number.")
        else:
            print("Invalid choice.")


# Conversation management
def list_conversations():
    files = [f for f in os.listdir(CONVERSATIONS_DIR) if f.endswith('.json')]
    return sorted(files)


def select_system_prompt():
    prompts = list_system_prompts()
    if not prompts:
        print("No system prompts available. Using no system prompt.")
        return None

    print("\nAvailable system prompts:")
    print("0. No system prompt")
    for i, name in enumerate(prompts):
        print(f"{i + 1}. {name}")

    while True:
        try:
            choice = input("\nSelect a system prompt (0 for none): ").strip()
            if choice == '0':
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(prompts):
                filepath = os.path.join(SYSTEM_PROMPTS_DIR, prompts[idx])
                with open(filepath, 'r') as f:
                    system_prompt = f.read()
                return {"name": prompts[idx], "content": system_prompt}
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a valid number.")


def new_conversation():
    name = input("Enter a name for the new conversation: ")
    filename = f"{name}.json" if not name.endswith('.json') else name
    filepath = os.path.join(CONVERSATIONS_DIR, filename)

    # Select system prompt
    print("\nWould you like to use a system prompt? (y/n): ")
    use_system_prompt = input().lower() == 'y'

    system_prompt = None
    if use_system_prompt:
        system_prompt = select_system_prompt()

    conversation = {
        "metadata": {
            "created_at": datetime.datetime.now().isoformat(),
            "model": config["API"]["model"],
            "name": name,
            "system_prompt": system_prompt
        },
        "messages": []
    }

    save_conversation(conversation, filepath)
    return conversation, filepath


def load_conversation(filename):
    filepath = os.path.join(CONVERSATIONS_DIR, filename)
    with open(filepath, 'r') as f:
        conversation = json.load(f)
    return conversation, filepath


def save_conversation(conversation, filepath):
    with open(filepath, 'w') as f:
        json.dump(conversation, f, indent=2)


def count_tokens(client, messages):
    """Count tokens for a given message list."""
    try:
        result = client.messages.count_tokens(
            model=config["API"]["model"],
            messages=messages
        )
        return result.input_tokens
    except Exception as e:
        print(f"Error counting tokens: {e}")
        return "Unknown"


def display_message(message, include_thinking=True):
    """Display a message with optional thinking content"""
    if message["role"] == "user":
        print(f"\n👤 You: {message['content']}")
    else:
        print(f"\n🔮 Claude: {message['content']}")
        if include_thinking and "thinking" in message and message["thinking"]:
            print(f"\n🧠 Thinking:\n{message['thinking']}")


def streaming_chat_loop(conversation, filepath, client):
    print(f"\nChat session: {conversation['metadata']['name']} (Streaming mode)")

    # Display system prompt if present
    if conversation["metadata"].get("system_prompt"):
        print(f"\nUsing system prompt: {conversation['metadata']['system_prompt']['name']}")

    print("Type 'exit' to return to the main menu.\n")

    # Display existing conversation
    for message in conversation["messages"]:
        display_message(message)

    # Prepare API-compatible messages list
    api_messages = []
    for msg in conversation["messages"]:
        api_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Get system prompt if available
    system_prompt = None
    if conversation["metadata"].get("system_prompt"):
        system_prompt = conversation["metadata"]["system_prompt"]["content"]

    while True:
        user_input = input("\n👤 You: ")
        if user_input.lower() == 'exit':
            break

        # Add user message to conversation and API messages
        timestamp = datetime.datetime.now().isoformat()
        conversation["messages"].append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })

        api_messages.append({
            "role": "user",
            "content": user_input
        })

        # Stream response from Claude API
        try:
            print("\nProcessing...\n")

            # For collecting the complete response
            current_thinking = ""
            current_response = ""
            in_thinking_block = False
            in_text_block = False

            # Prepare API call parameters
            api_params = {
                "model": config["API"]["model"],
                "temperature": float(config["Parameters"]["temperature"]),
                "max_tokens": int(config["Parameters"]["max_tokens"]),
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": int(config["Parameters"]["thinking_budget"])
                },
                "messages": api_messages
            }

            # Add system prompt if available
            if system_prompt:
                api_params["system"] = system_prompt

            with client.messages.stream(**api_params) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "thinking":
                            in_thinking_block = True
                            print("🧠 Thinking:")
                        elif event.content_block.type == "text":
                            in_text_block = True
                            in_thinking_block = False
                            print("\n🔮 Claude: ", end="", flush=True)

                    elif event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta" and in_thinking_block:
                            current_thinking += event.delta.thinking
                            print(event.delta.thinking, end="", flush=True)
                        elif event.delta.type == "text_delta" and in_text_block:
                            current_response += event.delta.text
                            print(event.delta.text, end="", flush=True)

                    elif event.type == "content_block_stop":
                        if in_thinking_block:
                            in_thinking_block = False
                            print("\n")  # Add spacing after thinking
                        elif in_text_block:
                            in_text_block = False
                            print()  # Add a newline after text

                    elif event.type == "message_stop":
                        pass

            # Add assistant response to conversation
            conversation["messages"].append({
                "role": "assistant",
                "content": current_response,
                "thinking": current_thinking,
                "timestamp": datetime.datetime.now().isoformat()
            })

            # Add to API messages for context
            api_messages.append({
                "role": "assistant",
                "content": current_response
            })

            # Save after each exchange
            save_conversation(conversation, filepath)

            # Show token count
            token_count = count_tokens(client, api_messages)
            print(f"\nCurrent conversation token count: {token_count}")

        except Exception as e:
            print(f"Error: {e}")


def configure_settings():
    print("\n===== Configuration =====")
    print("1. API Key")
    print("2. Model")
    print("3. Temperature")
    print("4. Max Tokens")
    print("5. Thinking Budget")
    print("0. Back")

    choice = input("\nEnter your choice: ").strip()

    if choice == '1':
        config["API"]["key"] = input("Enter your Claude API key: ")
    elif choice == '2':
        config["API"]["model"] = input(f"Enter model name (current: {config['API']['model']}): ") or config["API"][
            "model"]
    elif choice == '3':
        temp = input(f"Enter temperature (0-1, current: {config['Parameters']['temperature']}): ")
        if temp:
            config["Parameters"]["temperature"] = temp
    elif choice == '4':
        tokens = input(f"Enter max tokens (current: {config['Parameters']['max_tokens']}): ")
        if tokens:
            config["Parameters"]["max_tokens"] = tokens
    elif choice == '5':
        budget = input(f"Enter thinking budget (current: {config['Parameters']['thinking_budget']}): ")
        if budget:
            config["Parameters"]["thinking_budget"] = budget

    with open(CONFIG_FILE, 'w') as f:
        config.write(f)


# Main application
def main():
    global config, streaming_mode  # Declare globals at the beginning

    client = anthropic.Anthropic(api_key=config["API"]["key"])

    while True:
        print("\n===== Claude Chat Application =====")
        print("1. New Conversation")

        conversations = list_conversations()
        if conversations:
            print("2. Load Conversation")
            for i, name in enumerate(conversations):
                print(f"   {i + 1}. {name}")

        print("\nP. Manage System Prompts")
        print("S. Toggle Streaming Mode (Currently", "ON" if streaming_mode else "OFF", ")")
        print("C. Configure Settings")
        print("0. Exit")

        choice = input("\nEnter your choice: ").strip().lower()

        if choice == '0':
            break
        elif choice == '1':
            conversation, filepath = new_conversation()
            if streaming_mode:
                streaming_chat_loop(conversation, filepath, client)
            else:
                print("This model requires streaming mode to be ON. Switching to streaming mode.")
                streaming_mode = True
                streaming_chat_loop(conversation, filepath, client)
        elif choice == '2' and conversations:
            try:
                idx = int(input("Enter the number of the conversation to load: ")) - 1
                if 0 <= idx < len(conversations):
                    conversation, filepath = load_conversation(conversations[idx])
                    if streaming_mode:
                        streaming_chat_loop(conversation, filepath, client)
                    else:
                        print("This model requires streaming mode to be ON. Switching to streaming mode.")
                        streaming_mode = True
                        streaming_chat_loop(conversation, filepath, client)
                else:
                    print("Invalid conversation number.")
            except ValueError:
                print("Please enter a valid number.")
        elif choice == 'p':
            manage_system_prompts()
        elif choice == 's':
            if not streaming_mode:
                streaming_mode = True
                print("Streaming mode is now ON. (Required for this model)")
            else:
                print("WARNING: This model requires streaming mode to be ON.")
                confirm = input("Are you sure you want to turn it off? (y/n): ").lower()
                if confirm == 'y':
                    streaming_mode = False
                    print("Streaming mode is now OFF (not recommended)")
        elif choice == 'c':
            configure_settings()
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    try:
        # Initialize globals before use
        config = load_config()
        streaming_mode = True  # Default to streaming ON
        main()
    except KeyboardInterrupt:
        print("\nExiting application...")