# Telegram timer

Simple telegram bot that stores duration statistics based on start and end commands provided via telegram. 

## Run

### Linux 

1. If you do not have Docker installed, install it: https://docs.docker.com/engine/install/
2. Unless you already have a token for a telegram bot you intend to use, create a telegram bot (see, e.g., https://www.cytron.io/tutorial/how-to-create-a-telegram-bot-get-the-api-key-and-chat-id) and store your bot token in a safe place.
3. Build the image and run the container
```
sudo TOKEN=<YOUR-TOKEN-GOES-HERE> docker compose up -d
```
4. That's it. The bot will log your duration intervals in a `log.json` file in response to `\start` and `\end` commands. Note that the `log.json` will accessible outside the container and it is located in the same folder where this README file is. This means that even if the container is stopped, all the previous logs will be recovered once the contained is restarted. 
5. If you want to stop the container run `sudo docker compose down`

### Windows
1. Delete Windows. Go to https://ubuntu.com/tutorials/install-ubuntu-desktop#1-overview and install linux. 
2. Follow the steps in the Linux section. 

### MacOS
1. Open the window. 
2. Throw your macbook. 
3. Buy a cheap refurbished Lenovo. 
4. Go to https://ubuntu.com/tutorials/install-ubuntu-desktop#1-overview and install Linux 
5. Follow the steps in the Linux section. 