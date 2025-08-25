# Update Data Collecting Configuration
1. Go to Hyperbase integration page, then find the Configure option.
   
   ![onboarding-10](_media/onboarding-10.jpg ':size=80%')
2. Select "Download CSV Data" then press **Submit** to continue.
   
   ![onboarding-20](_media/onboarding-20.jpg ':size=40%')
3. Specify time of the oldest and latest data. The integration will read all "hass" collections in the Hyperbase. You can select one collection from **Collection Name** dropdown.
   
   !> **Caution!** Specifying a long time range for frequent data collecting might overwhelm. It is recommended to use 30 to 60 minutes time range.
   
   ![onboarding-21](_media/onboarding-21.jpg ':size=40%')

   **Home Assistant Base URL** is the base url you use to access HA web UI. You might need to change *localhost* into an IP address or hostname. Press **Submit** to continue
4. Copy the URL and **open the URL in a new Tab**. Wait for your CSV file.
   
   ![onboarding-22](_media/onboarding-22.jpg ':size=40%')