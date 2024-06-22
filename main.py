import google.generativeai as genai
from flask import Flask, request, jsonify
import requests
import os
import fitz

wa_token = os.environ.get("WA_TOKEN")
genai.configure(api_key=os.environ.get("GEN_API"))
phone_id = os.environ.get("PHONE_ID")
phone = os.environ.get("PHONE_NUMBER")
sender_phone_number = os.environ.get("sender_phone")
name = "Lucas Lima"  # The bot will consider this person as its owner or creator
bot_name = "Katarina"  # This will be the name of your bot, eg: "Hello I am Astro Bot"
model_name = "gemini-1.5-flash-latest"  # Switch to "gemini-1.0-pro" or any free model, if "gemini-1.5-flash" becomes paid in future.

app = Flask(__name__)

generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
]

model = genai.GenerativeModel(
    model_name=model_name,
    generation_config=generation_config,
    safety_settings=safety_settings,
)

convo = model.start_chat(history=[])

convo.send_message(f"""
Você é a {bot_name}, a especialista em iPhones da iPhoneBV! Sua missão é proporcionar uma experiência incrível e ajudar cada cliente a encontrar o iPhone perfeito. 

🌟 Aja como uma consultora especialista, confiante e amigável. Porem sejá objetiva, o cliente não quer ler uma redação.

Lembre-se:

* Apresente soluções, não faça interrogatórios. 
* Vá direto ao ponto, mas sempre de forma simpática e acolhedora. 😊
* Use seu conhecimento para apresentar os benefícios de cada iPhone e conduzir o cliente à decisão de compra.
* Crie frases chamativas que despertem o interesse e a vontade de ter um iPhone. ✨
* Se o cliente demonstrar interesse real em comprar, ajude-o a finalizar a compra.

**Somente quando a venda estiver prestes a ser concluída, transfira a conversa para o Supervisor.**

**Catálogo iPhoneBV:**

* **iPhone 14 Pro Max (a partir de R$ 7.599)
* **iPhone 14 Pro (a partir de R$ 6.899)
* **iPhone 14 Plus (a partir de R$ 6.299)
* **iPhone 14 (a partir de R$ 5.399)
* **iPhone 13 (a partir de R$ 4.499)
* **Cabo original (a partir de R$ 80.00)
* **Base carregadora (a partir de R$ 150.00)

Lembre-se: você é a {bot_name}, a especialista em iPhones pronta para ajudar cada cliente a encontrar o aparelho ideal! Boa sorte! 😄🚀""")


def send(answer, sender_phone_number):
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {wa_token}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": f"whatsapp:{phone}",  # Use the sender's phone number
        "type": "text",
        "text": {"body": f"{answer} - +{sender_phone_number}"},
    }

    response = requests.post(url, headers=headers, json=data)
    return response


def remove(*file_paths):
    for file in file_paths:
        if os.path.exists(file):
            os.remove(file)
        else:
            pass


@app.route("/", methods=["GET", "POST"])
def index():
    return "Bot"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        data = request.get_json()["entry"][0]["changes"][0]["value"]["messages"][0]
        sender_phone_number = data["from"]  # Get the phone number of the sender
        # send("Estou aqui.", sender_phone_number)
        if mode == "subscribe" and token == "BOT":
            return challenge, 200
        else:
            return "Failed", 403

    elif request.method == "POST":
        try:
            data = request.get_json()["entry"][0]["changes"][0]["value"]["messages"][0]
            sender_phone_number = data["from"]  # Get the phone number of the sender
            send("Estou aqui.", sender_phone_number)
            if data["type"] == "text":
                prompt = data["text"]["body"]
                convo.send_message(prompt)
                send(convo.last.text, sender_phone_number)
            else:
                media_url_endpoint = (
                    f'https://graph.facebook.com/v18.0/{data[data["type"]]["id"]}/'
                )
                headers = {"Authorization": f"Bearer {wa_token}"}
                media_response = requests.get(media_url_endpoint, headers=headers)
                media_url = media_response.json()["url"]
                media_download_response = requests.get(media_url, headers=headers)
                if data["type"] == "audio":
                    filename = "/tmp/temp_audio.mp3"
                elif data["type"] == "image":
                    filename = "/tmp/temp_image.jpg"
                elif data["type"] == "document":
                    doc = fitz.open(
                        stream=media_download_response.content, filetype="pdf"
                    )
                    for _, page in enumerate(doc):
                        destination = "/tmp/temp_image.jpg"
                        pix = page.get_pixmap()
                        pix.save(destination)
                        file = genai.upload_file(
                            path=destination, display_name="tempfile"
                        )
                        response = model.generate_content(["What is this", file])
                        answer = response._result.candidates[0].content.parts[0].text
                        convo.send_message(
                            f"This message is created by an llm model based on the image prompt of user, reply to the user based on this: {answer}"
                        )
                        send(convo.last.text)
                        remove(destination)
                else:
                    send("This format is not Supported by the bot ☹")
                with open(filename, "wb") as temp_media:
                    temp_media.write(media_download_response.content)
                file = genai.upload_file(path=filename, display_name="tempfile")
                response = model.generate_content(["What is this", file])
                answer = response._result.candidates[0].content.parts[0].text
                remove("/tmp/temp_image.jpg", "/tmp/temp_audio.mp3")
                convo.send_message(
                    f"This is an voice/image message from user transcribed by an llm model, reply to the user based on the transcription: {answer}"
                )
                send(convo.last.text)
                files = genai.list_files()
                for file in files:
                    file.delete()
        except:
            pass
        return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=8000)
