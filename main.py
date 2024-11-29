from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
import openai
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Set OpenAI API key
openai.api_key = api_key

# Initialize FastAPI app
app = FastAPI()

# Set up templates directory
templates = Jinja2Templates(directory="Templates")

# Chat responses and logs
chat_responses = []
chat_log = [
    {
        'role': 'system',
        'content': (
            "You are a Python tutor AI, completely dedicated to teaching Python concepts, "
            "best practices, and real-world applications. When answering questions, always format your responses "
            "in a structured format with headings and subheadings. Use Markdown for formatting. "
            "Example of a response format:\n\n"
            "### Sure, here's a structured roadmap to learn Python:\n\n"
            "#### Understanding the Basics\n"
            "- Installation of Python\n"
            "- Understanding Python syntax\n"
            "- Variables and data types in Python\n\n"
            "#### Flow Control\n"
            "- Conditional statements: `if`, `elif`, `else`\n"
            "- Looping: `for`, `while`\n\n"
            "#### Data Structures\n"
            "- Lists\n"
            "- Tuples\n"
            "- Dictionaries\n"
            "- Sets\n\n"
            "Continue the format for other sections. Always use bullet points, headings, and code snippets when applicable."
        )
    }
]

# Route to serve the chat page
@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

# WebSocket for handling live chat
@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            user_input = await websocket.receive_text()
            chat_log.append({'role': 'user', 'content': user_input})

            # Send "Typing..." feedback to the frontend (handled by JS now)
            # await websocket.send_text("Typing...")  # Removed

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=chat_log,
                temperature=0.2,
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
            chat_log.append({'role': 'assistant', 'content': ai_response})

            # Also update chat_responses to display in the frontend
            chat_responses.append(user_input)  # Add user's input to the chat history
            chat_responses.append(ai_response)  # Add AI response to the chat history

        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(error_message)
            await websocket.send_text(error_message)
            break

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
