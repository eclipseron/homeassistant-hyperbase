# Hyperbase Integration for Home Assistant
Integration component for [Hyperbase](https://github.com/HyperbaseApp/hyperbase) local IoT data center system. Perform Iot devices data collecting without complex database configurations.


## :wrench: Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=eclipseron&repository=homeassistant-hyperbase&category=integration)

1. Open **HACS** in Home Assistant
2. Find **"Custom repositories"** in the option
3. Enter `https://github.com/eclipseron/homeassistant-hyperbase.git`. Choose **"Integration"** for the Type input.
4. Click **Add**.
5. Search for **"Hyperbase"** in HACS. Press **Download** and restart your HA.
6. Go to **Settings > Devices & services > + Add integration**.
7. Find **"Hyperbase"** and start the integration setup.


## :gear: Initial Setup

### :one: Hyperbase Setup

You can follow Hyperbase installation guide from [documentation](https://hyperbase-book.hilmy.dev/03_installation/04_setup/04_hyperbase) to create your Hyperbase instance. Once the installation ready, create new Hyperbase admin account and login. Now, you can [create a new Project](https://hyperbase-book.hilmy.dev/02_quick_start/04_create_project).

1. Inside the new project, you can find a "User" collection that is already created. Select the "User" collection and **Insert a record**.
  <img src="docs/_media/onboarding-1.jpg" style="width: 80%;" alt="onboarding-1"/>

1. Enter a username and password to identify the owner of each records. You can use your Home Assistant account or create new one. This user record be used to authorize MQTT publish from HA. Hit the save button when you are done.
  <img src="docs/_media/onboarding-2.jpg" style="width: 80%;" alt="onboarding-3"/>

3. You can find three-dots icon <img src="docs/_media/options-icon.jpg" style="width: 3%;" alt="options-icon"/> on the right side of the "User" collection. Click it and choose **Edit**.
  <img src="docs/_media/onboarding-3.jpg" style="width: 80%;" alt="onboarding-3"/>

4. Check the **Using the _id field to authenticate MQTT publishers** option then press **Edit**.
  <img src="docs/_media/onboarding-4.jpg" style="width: 50%;" alt="onboarding-4"/>

### :two: Create New Hyperbase Integration

1. On the Home Assistant web UI, go to **Settings > Devices & services > Add integration**. Search for "Hyperbase" and select the integration.
  <img src="docs/_media/onboarding-5.jpg" style="width: 50%;" alt="onboarding-5"/>

2. Fill all required fields with your Hyperbase configuration. Press **Submit** to continue.
> Hyperbase Base URL **is not** URL of the Hyperbase UI but [Hyperbase server](https://hyperbase-book.hilmy.dev/04_features/12_change_server).

  <img src="docs/_media/onboarding-7.jpg" style="width: 50%;" alt="onboarding-7"/>

3. Enter your Hyperbase administrator credentials into email and password fields. **Hyperbase Project ID** and **Home Assistant User ID** can be found here:
  <img src="docs/_media/onboarding-8.jpg" style="width: 80%;" alt="onboarding-8"/>

4. Press **Submit** and wait for the start up process. You can access Hyperbase integration service by clicking the card on Integrations page (**Settings > Devices & services**).
  <img src="docs/_media/onboarding-9.jpg" style="width: 80%;" alt="onboarding-9"/>



## :pencil2: Features
- **Connected with Hyperbase**: Configure Hyperbase connection through UI without coding needed.
- **Full Control Over Your Data**: Choose what information you need to store, change whenever you want.
- **Regular Consistency Check**: Regularly check connection between HA and Hyperbase. Data collecting failures handled with no worries.


## :book: Documentation
Hyperbase Documentation: https://github.com/HyperbaseApp/hyperbase

Hyperbase for HA Documentation: https://eclipseron.github.io/homeassistant-hyperbase
