# Snow Tickets
Apstra Anomalies provide an easy way to observe problems in the network fabric.
Service Now is a popular platform to report problems. This automation tracks the fabric and opens tickets in Service Now if there are problems.


## Requirements

- Apstra 4.2.0 or above
- python 3 or above

## Usage

1. Prepare the PowerPack
- Apstra needs to have a Property Set that is used to manage the power pack. 
- This can be auto-installed with Terraform or done manually
    
    1.2. Setting up Apstra with Terraform
    - Fill out apstra_snow_setup.sh
    - % source apstra_snow_setup.sh
    - % terraform init&&terraform apply
    - This will set up a Property Set called Ticket Manager with all the blueprints in the environment.
    - Inspect the Property Set and ensure that only the blueprints you want to track are in the list

    1.3 Setting up Apstra manually.
    - Set up the management property set in Apstra with appropriate values
    ![img.png](img.png)

2. Run PowerPack with Docker 
- copy setup.yaml.template to setup.yaml. Fill in the values as appropriate
- Export the APSTRA_PASS and SNOW_PASS passwords
- % docker build .  
  - At the end of this commend, you will get the id of the image that just got built use it in the next step
- docker run  -v $PWD/setup.yaml:/SnowApp/setup.yaml -e APSTRA_PASS=$APSTRA_PASS -e SNOW_PASS=$SNOW_PASS -e APSTRA_URL=$APSTRA_URL -e APSTRA_USER=$APSTRA_USER -e APSTRA_PORT=$APSTRA_PORT  <docker image id from previous step>

3. Run PowerPack from Commandline
- % pip3 install -r ./requirements.txt
- copy setup.yaml.template to setup.yaml. Fill in the values as appropriate
- Export the APSTRA_PASS and SNOW_PASS passwords
- start the python script 
   % python snow_tickets.py


