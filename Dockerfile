   FROM python:3.11
   
   # Install Rust compiler for tiktoken
   RUN apt-get update && apt-get install -y curl build-essential
   RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
   ENV PATH="/root/.cargo/bin:${PATH}"
   
   WORKDIR /app
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
   
   # Copy app code
   COPY . .
   
   # Expose port and run Streamlit
   EXPOSE 8501
   CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]