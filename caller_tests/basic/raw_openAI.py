from openai import OpenAI

client = OpenAI()  # requires OPENAI_API_KEY

model = "gpt-4.1"

messages = [
    {
        "role": "user",
        "content": "give me a random number between 1 and 100. just output the number.",
    }
]
chat = client.chat.completions.create(model=model, messages=messages, seed=1, temperature=0, n=10)
print(f"Run:")
choices = set()
for choice in chat.choices:
    choices.add(choice.message.content)
