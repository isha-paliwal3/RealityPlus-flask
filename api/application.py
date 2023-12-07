import os
from time import sleep
from packaging import version
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Check OpenAI version is correct
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if current_version < required_version:
  raise ValueError(f"Error: OpenAI version {openai.__version__}"
                   " is less than the required version 1.1.1")
else:
  print("OpenAI version is compatible.")

# Start Flask app
app = Flask(__name__)

origins = [
    "http://localhost:3000",
    "https://reality-plus-web.vercel.app"
]

CORS(app, origins=origins)
# Init client
client = OpenAI(api_key=OPENAI_API_KEY)

def createAssistant(client, instructions):

  assistant = client.beta.assistants.create(
    instructions=instructions,
    model="gpt-4-1106-preview",
    )
  
  assistant_id = assistant.id
  
  return assistant_id

@app.route('/createAssistant', methods=['POST'])
def create_assistant():
  data = request.json
  instructions = data.get('instructions', '')

  if not instructions:
    return jsonify({"error": "Missing instructions"}), 400

  assistant_id = createAssistant(client, instructions)
  return jsonify({"assistant_id": assistant_id})


@app.route('/start', methods=['POST'])
def start_conversation():
  data = request.json
  assistant_id = data.get('assistant_id')

  if not assistant_id:
    return jsonify({"error": "Missing assistant_id"}), 400

  thread = client.beta.threads.create()
  return jsonify({"thread_id": thread.id})


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json

    def generate(data):
        thread_id = data.get('thread_id')
        assistant_id = data.get('assistant_id')
        user_input = data.get('message', '')

        if not thread_id:
            yield f"data: Error: Missing thread_id\n\n"
            return

        print(f"Received message: {user_input} for thread ID: {thread_id}")

        client.beta.threads.messages.create(thread_id=thread_id,
                                            role="user",
                                            content=user_input)

        run = client.beta.threads.runs.create(thread_id=thread_id,
                                              assistant_id=assistant_id)

        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                          run_id=run.id)
            print(f"Run status: {run_status.status}")
            if run_status.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                response = messages.data[0].content[0].text.value
                yield f"{response}\n\n"
                break
            sleep(1)

    return Response(generate(data), mimetype='text/event-stream')

# Run server
if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)

