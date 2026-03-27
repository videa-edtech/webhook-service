#? |-----------------------------------------------------------------------------------------------|
#? |  main.py                                                                                      |
#? |                                                                                               |
#? |  Copyright (c) 2021 Belikhun. All right reserved                                              |
#? |  Licensed under the MIT License. See LICENSE in the project root for license information.     |
#? |-----------------------------------------------------------------------------------------------|

import libs.ehook
from libs.log import log

from colorama import init, Fore
log("OKAY", "Imported: colorama")

from webhook import Webhook
log("OKAY", "Imported: webhook")

import json
log("OKAY", "Imported: json")

import os
log("OKAY", "Imported: os")

import shutil
log("OKAY", "Imported: shutil")

from flask import Flask, abort
log("OKAY", "Imported: flask")

from subprocess import Popen, PIPE
log("OKAY", "Imported: subprocess")

from multiprocessing import Process, Queue
log("OKAY", "Imported: multiprocessing")

import getpass
log("OKAY", "Imported: getpass")
log("INFO", f"Starting Webhook Listener as {getpass.getuser()}")

log("INFO", "Reading Configuration File")
config = {}

if (not os.path.isfile("config.json")):
    log("WARN", "config.json not found! Creating from default")
    shutil.copyfile("config.default.json", "config.json")

with open("config.json", "r", encoding = "utf-8") as file:
	try:
		config = json.loads(file.read())
	except ValueError:
		log("ERRR", "Errored While Reading Configuration File")
		log("ERRR", "{} → Reason: {}JSON Decode Error (config.json)".format(Fore.WHITE, Fore.LIGHTBLACK_EX))
		exit(-1)

app = Flask(__name__)
webhook = Webhook(app, endpoint=config['endpoint'])

@app.route("/")
def index():
    abort(501)

@webhook.hook(event_type="ping")
def on_ping(data):
    repo = data["repository"]["full_name"]

    log("INFO", f"PONG! From {repo}")

    if (repo not in config["repos"]):
        log("WARN", f"No configuration found for repo {repo}. Configure it in config.json")
        return f"No configuration found for {repo}!", 500

    return "PONG!", 200

# On Push to repository event
@webhook.hook(event_type="push")
def on_push(data):
    repo = data["repository"]["full_name"]

    if (repo not in config["repos"]):
        log("WARN", f"No configuration found for repo {repo}. Configure it in config.json")
        return f"No configuration found for {repo}!", 500

    log("INFO", f"Received push from {repo} ref {data['ref']} triggered by {data['pusher']['name']}")

    ref = data["ref"]

    if (not ref.startswith("refs/heads/")):
        log("INFO", f"Skipping this webhook since ref {ref} is not a branch ref.")
        return "No Update", 200

    branch = ref[len("refs/heads/"):]
    repoConfig = config["repos"][repo]

    if (branch in repoConfig):
        p = Process(target=handle_push, args=(repo, branch, repoConfig[branch]))
        p.start()

        return "Success", 200

    log("INFO", f"Skipping this webhook since branch {branch} is not configured for {repo}.")
    return "No Update", 200

def handle_push(repo, branch, branchConfig):
    commands = branchConfig["command"]
    path = branchConfig["path"]

    log("INFO", f"Handling push for {repo} branch {branch}")

    for command in commands:
        log("INFO", f"Executing Command: {Fore.LIGHTYELLOW_EX}\"{command}\" {Fore.WHITE}at {Fore.LIGHTCYAN_EX}\"{path}\"")

        process = Popen(command.split(" "), cwd=path, stdout=PIPE)
        (output, error) = process.communicate()
        exitCode = process.wait()

        output = output.decode("utf-8")

        if (exitCode != 0 or ("ERROR" in output) or error != None):
            log("ERRR", "{} → ProcessError: {}\"{}\" returned non-zero status code: {}".format(Fore.LIGHTRED_EX, Fore.LIGHTBLACK_EX, command, str(exitCode)))
            log("ERRR", f"   STDOUT: {output}")
            log("ERRR", f"   STDERR: {error}")
            raise Exception(f"Process returned bad status code: {exitCode}")

        log("OKAY", "Command Completed Successfully")

        # Line By Line Logging
        outputLines = output.split("\n")
        for line in outputLines:
            log("DEBG", f"\t{Fore.LIGHTBLACK_EX}{line}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config["port"])
