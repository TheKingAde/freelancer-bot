import g4f
from g4f.Provider import Yqcloud

response = g4f.ChatCompletion.create(
    model="gpt-4",
    provider=Yqcloud,
    messages=[
        {"role": "user", "content": "Write a short cover letter for a Python freelance job"}
    ]
)

print(response)
