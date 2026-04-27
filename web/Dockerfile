# Use the official Python 3.9 image
FROM python:3.9

# Create a user with ID 1000 to match the HF Spaces environment
RUN useradd -m -u 1000 user
USER user

# Set environment variables
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR $HOME/app

# Copy the requirements file and install dependencies
COPY --chown=user ./requirements.txt $HOME/app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install gunicorn

# Copy the rest of the application files
COPY --chown=user . $HOME/app

# Start the application using Gunicorn, listening on port 7860
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:7860", "app:server", "--timeout", "120"]
