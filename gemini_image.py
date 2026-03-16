from google import genai
from google.genai import types
from PIL import Image
import base64

client = genai.Client(api_key="AIzaSyDUcz_dPduCScarQpElQB6H3MaKzK3LAZs")

def generate_image(prompt, reference_path, output_path):

    reference = Image.open(reference_path)

    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=[prompt, reference],
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio="1:1",
            )
        )
    )

    for part in response.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = part.as_image()
            image.save(output_path)