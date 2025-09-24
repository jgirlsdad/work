# Pulled from https://dev.socrata.com/docs/other/publishing#?route=overview

import os
import requests
import pandas
from dotenv import load_dotenv
from operator import itemgetter
load_dotenv()

# Setup environment
domain_url = 'https://data.colorado.gov' # Set your domain
census_ids = pandas.read_csv("census_ids.csv")
for index, row in census_ids.iterrows():
  print(row['Socrata Link'])
  fourfour = row['Socrata Link']
  credentials = (os.environ['USERNAME'], os.environ['PASSWORD'])

  # Get list of defined field descriptions
  field_descriptions = pandas.read_csv("census_field_descriptions.csv")

  # Create revision on CIM to work with
  replace_json = {
      'action': {
          'type': 'replace',
      }
  }

  replace_response = requests.post(f'{domain_url}/api/publishing/v1/revision/{fourfour}', json=replace_json, auth=credentials)

  # Update the revision to have the current data on CIM (don't change the data, just the metadata)
  create_source_link = replace_response.json()['links']['create_source']
  create_source_json = {
      'source_type': {
          'type': 'view',
          'fourfour': fourfour
      }
  }
  create_source_response = requests.post(domain_url + create_source_link, json=create_source_json, auth=credentials)

  # Extract current metadata
  input_schemas = create_source_response.json()['resource']['schemas']
  latest_input_schema = max(input_schemas, key=itemgetter('id'))
  output_schemas = latest_input_schema['output_schemas']
  latest_output_schema = max(output_schemas, key=itemgetter('id'))

  # Transform schema of specific row
  updated_columns = latest_output_schema['output_columns']
  for c in updated_columns:
    # skip anything that already has a description
    if not c.get("description"):
      # get matching description
      field = field_descriptions.query(f"APIFieldName=='{c.get('field_name')}'")
      if not field.empty:
        # set matching description
        c["description"] = field.iloc[0].get('description')
      else:
        print(f"Warning: field description not found: {c.get('field_name')}")
    else:
      print(f"Warning: description already set, ignoring...")

  # Post updated field descriptions to the revision
  updated_schema = {
      'output_columns': updated_columns
  }
  input_schema_id = latest_input_schema['id']
  transform_schema_link = create_source_response.json()     ['links']['input_schema_links']['transform'].format(input_schema_id=input_schema_id)
  transform_schema_response = requests.post(domain_url + transform_schema_link, json=updated_schema, auth=credentials)

  # Apply and close revision
  apply_json = {'output_schema_id': transform_schema_response.json()['resource']['id']}
  apply_link = replace_response.json()['links']['apply']
  apply_response = requests.put(domain_url + apply_link, auth=credentials)