## Home Assistant Quick Install

We are still working on component publication with HACS and Home Assistant Add-Ons. You can use Home Assistant on docker installation guide to setup your environment [here](https://www.home-assistant.io/installation/linux). You also can use the following `compose.yaml` file:
```yaml
services:
  homeassistant:
    container_name: homeassistant
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - /PATH_TO_YOUR_CONFIG:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
```
Start the docker container by:
```bash
docker compose up -d
```

You can access the web UI from http://YOUR-IP:8123. Follow the onboarding process and you Home Assistant instance is ready.

## Hyperbase for HA Installation

Once you have your Home Assistant container running, use this command to access bash from the container. You might use `sudo` if the command not working.

```bash
docker exec -it <container_name> bash
```

Then, go into the config directory and create `custom_components` directory if not exists. Use the following command:

```bash
mkdir /config/custom_components
cd /config/custom_components
```

Run git command to clone the custom component repository

```bash
git clone https://github.com/eclipseron/homeassistant-hyperbase.git hyperbase
```

Restart your Home Assistant from web UI or using the following command:

```bash
docker restart <container_name>
```

<!-- Go to **Settings > Devices & services > Add integration** and search for Hyperbase.

![Hyperbase Integration](_media/hyperbase-integration.png ':size=50%') -->

## Hyperbase Setup

You can follow Hyperbase installation guide from [documentation](https://hyperbase-book.hilmy.dev/03_installation/04_setup/04_hyperbase) to create your Hyperbase instance. Once the installation ready, create new Hyperbase admin account and login. Now, you can [create a new Project](https://hyperbase-book.hilmy.dev/02_quick_start/04_create_project).

1. Inside the new project, you can find a "User" collection that is already created. Select the "User" collection and **Insert a record**.
  
  ![onboarding-1](_media/onboarding-1.jpg ':size=80%')

2. Enter a username and password to identify the owner of each records. You can use your Home Assistant account or create new one. This user record be used to authorize MQTT publish from HA. Hit the save button when you are done.
  
  ![onboarding-2](_media/onboarding-2.jpg ':size=80%')

3. You can find three-dots icon ![icon](_media/options-icon.jpg ':size=2%') on the right side of the "User" collection. Click it and choose **Edit**.
  
  ![onboarding-3](_media/onboarding-3.jpg ':size=80%')

4. Check the **Using the _id field to authenticate MQTT publishers** option then press **Edit**.
  ![onboarding-4](_media/onboarding-4.jpg ':size=50%')

## Create New Hyperbase Integration

1. On the Home Assistant web UI, go to **Settings > Devices & services > Add integration**. Search for "Hyperbase" and select the integration.
  
  ![onboarding-5](_media/onboarding-5.jpg ':size=50%')
2. Fill all required fields with your Hyperbase configuration. Press **Submit** to continue.

?> Hyperbase Base URL **is not** URL of the Hyperbase UI but [Hyperbase server](https://hyperbase-book.hilmy.dev/04_features/12_change_server).

  ![onboarding-7](_media/onboarding-7.jpg ':size=50%')

3. Enter your Hyperbase administrator credentials into email and password fields. **Hyperbase Project ID** and **Home Assistant User ID** can be found here:

  ![onboarding-8](_media/onboarding-8.jpg ':size=80%')
4. Press **Submit** and wait for the start up process. You can access Hyperbase integration service by clicking the card on Integrations page (**Settings > Devices & services**).

  ![onboarding-9](_media/onboarding-9.jpg ':size=80%')
