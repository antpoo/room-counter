# importing dependent libraries
from flask import Flask, render_template
import os


# creating flask app object
app = Flask(__main__)

# route to home page
@app.route("/")
def main():
    return render_template("home.html")


# main code 
if __name__ == "__main__":
    
    # run the flask app
    app.run(host = "0.0.0.0", port=5000)