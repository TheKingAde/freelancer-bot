import g4f
from g4f.Provider import Yqcloud, Blackbox, PollinationsAI, OIVSCodeSer2, WeWordle

# Prompt to test
prompt = """
Write a freelance job proposal message for the project below:

project = {
    Title: Portfolio Site Development

    Description: I'm seeking a skilled web developer to create a professional portfolio website. The primary goal of this site is to attract potential clients or employers. The website should include the following sections: About Me - Services Offered - Client Testimonials. Ideal skills and experience - Proven experience in creating portfolio websites - Strong design skills to ensure a professional look - Ability to write compelling content for each section"
}

The message should:
- Be between 100 and 1000 characters
- Sound friendly and human
- Start with "Hello," then a new line, Don't use Dear [Client] or Don't use Hello [Client]
- use the word "I" only when needed so it sound like it is typed by a human freelancer applying for a job
- Don't list anything, write everything in paragraph form
- Include a brief high-level summary of how I would approach the project
- Mention possible solutions where relevant (but avoid technical detail)
- Don't use exclamation marks, emojis or Best regards [Your Name]
- use Thanks at the end
"""

# Providers and models
tests = [
    {"provider": Yqcloud, "model": "gpt-4", "label": "Yqcloud - GPT-4"},
    {"provider": Blackbox, "model": "gpt-4", "label": "Blackbox - GPT-4"},
    {"provider": PollinationsAI, "model": None, "label": "PollinationsAI - DEFAULT"},
    {"provider": OIVSCodeSer2, "model": "gpt-4o-mini", "label": "OIVSCodeSer2 - gpt-4o-mini"},
    {"provider": WeWordle, "model": "gpt-4", "label": "WeWordle - GPT-4"},
]

for test in tests:
    try:
        print(f"--- Trying {test['label']} ---")
        kwargs = {
            "provider": test["provider"],
            "messages": [{"role": "user", "content": prompt}]
        }
        if test["model"]:
            kwargs["model"] = test["model"]

        response = g4f.ChatCompletion.create(**kwargs)

        if response and isinstance(response, str) and response.strip():
            print(response)
            break  # Stop once a valid response is received
    except Exception as e:
        print(f"❌ Error with {test['label']}: {e}")
    print('-' * 80)

