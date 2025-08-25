# Start Collecting Device Data

1. Go to Hyperbase integration page, then find the Configure option.
   
   ![onboarding-10](_media/onboarding-10.jpg ':size=80%')
2. Select **Register New Device** then press **Submit** to continue.
   
   ![onboarding-12](_media/onboarding-12.jpg ':size=40%')
3. You can choose any device from **Available Devices**. Remember to enable the device before you add it into Hyperbase integration. Press **Submit** to continue.
   
   ![onboarding-13](_media/onboarding-13.jpg ':size=40%')
4. **Connector Entity ID** is used to identify each data collecting pipeline from device to Hyperbase. It must be unique within your Home Assistant instance. It is recommended to leave connector id as default.
   
   ![onboarding-11](_media/onboarding-11.jpg ':size=40%')
5. You can choose entities to be collected. One at most per category.
   
   ![onboarding-14](_media/onboarding-14.jpg ':size=40%')
6. Specify the time interval between each data storing. The minimum of time interval is 1 second. Decreasing time interval will increase data resolution, but it also will increase the stored data in the Hyperbase.
7. Check **Add another device** to add next device or **Submit** to finish the configuration. 
