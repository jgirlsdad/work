# field_descriptions

The purpose of this code base is to demonstrate and utilize automation in updating field descriptions

## Current State (to be updated)

`main.py` has code for how to add CIM field descriptions. It goes through the following steps:

- Create a revision for a given dataset
- Update the revision with the current data on CIM for the given dataset
- Pull the current fields and descriptions
- Update the field descriptions based on `census_field_descriptions.csv`, matching csv `APIFieldName` with CIM `field_name`
- Post the updated field descriptions back to CIM
- Approve and close the revision

### Authentication

The `.env` file needs to have a `USERNAME` and `PASSWORD` values. These are not the web username and password, but rather
a Socrata API key ID and key secret. Please request from team technical lead if you do not have it. It should look like

```
USERNAME=xxxxxxxxxxxxxxxxxx
PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## What still needs to be done?

We want to automate this, such that we can loop over all census datasets and get field descriptions synced up.
However, we do need to get a clean list of where the census datasets are (many in the dataset tracker are maps).
See https://xentity.atlassian.net/browse/BIC-699 for completing this work.

Once that work is complete, we can create a list of datasets to process, and turn the main.py into
a function that processes all the census datasets.

Eventually we should try to sync all the metadata on the [BIC Dataset Tracker](https://docs.google.com/spreadsheets/d/1B2PvO4Q3eegdgPKG297SUA1i_b1nj7Ltq2SBoJEDGmY/edit#gid=2003186102), but that's TBD.