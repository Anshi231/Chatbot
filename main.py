from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
import openai
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from typing import Dict

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Set OpenAI API key
openai.api_key = api_key

# Initialize FastAPI app
app = FastAPI()

# Set up templates directory
templates = Jinja2Templates(directory="Templates")

# Chat logs stored per client (simple implementation)
client_chat_logs: Dict[str, Dict] = {}

# Route to serve the chat page
@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    # Retrieve chat_responses from session or initialize empty list
    chat_responses = []
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

# WebSocket for handling live chat
@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    if client_id not in client_chat_logs:
        client_chat_logs[client_id] = {
            'chat_log': [
                {
                    'role': 'system',
                    'content': (
                        'You are a Python tutor AI, completely dedicated to teaching Python concepts, '
                        'best practices, and real-world applications. When answering questions, always format lists as numbered or bulleted lists with proper indentation for clarity. Use Markdown for formatting where applicable. Also, whenever any code is there, always highlight it using triple backticks.'
                    )
                }
            ],
            'chat_responses': []
        }

    client_data = client_chat_logs[client_id]

    try:
        while True:
            user_input = await websocket.receive_text()
            client_data['chat_log'].append({'role': 'user', 'content': user_input})

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=client_data['chat_log'],
                temperature=0.6,
                stream=True
            )

            ai_response = ''

            # Collect all chunks into ai_response
            for chunk in response:
                if 'delta' in chunk.choices[0] and 'content' in chunk.choices[0].delta:
                    ai_content = chunk.choices[0].delta.content
                    ai_response += ai_content

            # Send the complete response to the frontend
            await websocket.send_text(ai_response)

            # Append full AI response to the chat log
            client_data['chat_log'].append({'role': 'assistant', 'content': ai_response})

            # Also update chat_responses to display in the frontend
            client_data['chat_responses'].append({'role': 'user', 'content': user_input})  # Add user's input
            client_data['chat_responses'].append({'role': 'assistant', 'content': ai_response})  # Add AI response

    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected.")
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        await websocket.send_text(error_message)

# Route to serve the image generation page
@app.get("/image", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image.html", {"request": request, "image_url": None})

# Route to handle image generation based on user input
@app.post("/image")
async def generate_image(request: Request, user_input: str = Form(...)):
    try:
        # Call OpenAI API for image generation (DALL·E model)
        response = openai.Image.create(
            prompt=user_input,
            n=1,
            size="512x512"
        )

        # Get the image URL from the response
        image_url = response['data'][0]['url']

        # Return the image generation page with the image URL
        return templates.TemplateResponse("image.html", {"request": request, "image_url": image_url})

    except Exception as e:
        error_message = f"Error generating image: {str(e)}"
        print(error_message)
        return templates.TemplateResponse("image.html", {"request": request, "image_url": None, "error_message": error_message})
