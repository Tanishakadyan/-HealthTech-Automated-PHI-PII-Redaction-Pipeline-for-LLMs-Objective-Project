import re

text = """
Patient John Smith
Email: johnsmith@gmail.com
"""

email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

emails = re.findall(email_pattern, text)

print(emails)
