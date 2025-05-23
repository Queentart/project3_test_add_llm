import json
import urllib.request
import base64
import io
from PIL import Image
import websocket

# Configuration - UPDATE THIS TO THE IP OF THE COMFYUI SERVER
server_address = "127.0.0.1:8188"

def load_workflow(filename="workflow.json"):
    with open(filename, 'r') as file:
        return json.load(file)

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def update_workflow_with_image(workflow, image_path):
    base64_image = encode_image_to_base64(image_path)
    # UPDATE THIS VALUE DEPENDING ON THE NODE ID
    workflow["10"]["inputs"]["image"] = base64_image
    return workflow

def queue_prompt(prompt):
    data = json.dumps({"prompt": prompt}).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response body: {e.read().decode('utf-8')}")
        raise

def get_image(prompt_id):
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws")
    
    print(f"Waiting for image data for prompt ID: {prompt_id}")
    
    while True:
        message = ws.recv()
        if isinstance(message, str):
            data = json.loads(message)
            print(f"Received message: {data}")
            if data['type'] == 'executing':
                if data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
                    print("Execution completed")
                    break
        elif isinstance(message, bytes):
            print("Received binary data (likely image)")
            image = Image.open(io.BytesIO(message[8:]))  # Skip first 8 bytes (message type)
            ws.close()
            return image
    
    ws.close()
    return None

# Load workflow from JSON file
workflow = load_workflow()
print("Workflow loaded successfully.")

# Specify the path to the image you want to upload
input_image_path = "sample-image.png"  # Make sure this file exists

# Update the workflow with the input image
workflow = update_workflow_with_image(workflow, input_image_path)
print("Workflow updated with input image.")

# Generate image
response = queue_prompt(workflow)
prompt_id = response['prompt_id']
print(f"Prompt queued with ID: {prompt_id}")

image = get_image(prompt_id)
if image:
    output_filename = "generated_image.png"
    image.save(output_filename)
    print(f"Image saved as {output_filename}")
    print(f"Image size: {image.size}")
    print(f"Image mode: {image.mode}")
else:
    print("Failed to retrieve image")

print("Script execution completed.")
