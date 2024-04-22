# Install dependencies
install:
    pip install -r requirements.txt

# Run the project
run:
    python main.py

# Clean up generated files
clean:
    rm -rf __pycache__