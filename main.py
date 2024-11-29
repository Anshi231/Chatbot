from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
import openai
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Set OpenAI API key
openai.api_key = api_key

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Set up templates and static files directories
templates = Jinja2Templates(directory="Templates")

# Chat responses and logs
class ChatManager:
    def __init__(self):
        self.chat_responses = []
        self.chat_log = [
            {
                'role': 'system',
                'content': (
                    "You are a Python tutor AI, completely dedicated to teaching Python concepts, "
                    "best practices, and real-world applications. Respond with clear, structured explanations. "
                    "Use markdown formatting for readability. Provide detailed, accurate information."
                )
            }
        ]

    def add_user_message(self, message):
        self.chat_responses.append({
            'type': 'user',
            'content': message
        })
        self.chat_log.append({'role': 'user', 'content': message})

    def add_ai_message(self, message):
        self.chat_responses.append({
            'type': 'ai',
            'content': message
        })
        self.chat_log.append({'role': 'assistant', 'content': message})

    def get_chat_responses(self):
        return self.chat_responses

# Create a global chat manager
chat_manager = ChatManager()

# Route to serve the chat page
@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "chat_responses": chat_manager.get_chat_responses()
    })

# WebSocket for handling live chat
@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            # Receive user input
            user_input = await websocket.receive_text()
            
            # Add user message to chat manager
            chat_manager.add_user_message(user_input)

            try:
                # Call OpenAI API
                response = openai.ChatCompletion.create(
                    model='gpt-4',
                    messages=chat_manager.chat_log,
                    temperature=0.2,
                    stream=True
                )

                # Collect AI response
                ai_response = ''
                for chunk in response:
                    if 'delta' in chunk.choices[0] and 'content' in chunk.choices[0].delta:
                        ai_content = chunk.choices[0].delta.content
                        ai_response += ai_content
                        # Optional: Send partial responses
                        # await websocket.send_text(ai_content)

                # Add full AI response to chat manager
                chat_manager.add_ai_message(ai_response)

                # Send complete response to client
                await websocket.send_text(ai_response)

            except Exception as api_error:
                error_message = f"OpenAI API Error: {str(api_error)}"
                print(error_message)
                await websocket.send_text(error_message)

        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        except Exception as e:
            error_message = f"WebSocket Error: {str(e)}"
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
