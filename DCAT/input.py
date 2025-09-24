import streamlit as st

prefixes = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "prov": "http://www.w3.org/ns/prov#",
    "locn": "http://www.w3.org/ns/locn#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "adms": "http://www.w3.org/ns/adms#",
    "schema": "http://schema.org/",
    "geo": "http://www.opengis.net/ont/geosparql#",
    "time": "http://www.w3.org/2006/time#"
}

# Set the title of the web page
st.title("Creating a DCAT Catalog")

# DCAT Catalog properties lookup
catalog_properties = {
    "title": {"prefix": "dct:title", "description": "Title of the catalog", "required": "Required"},
    "description": {"prefix": "dct:description", "description": "Description of the catalog", "required": "Required"},
    "publisher": {"prefix": "dct:publisher", "description": "Publisher of the catalog", "required": "Required"},
    "dataset": {"prefix": "dcat:dataset", "description": "Links to datasets in the catalog", "required": "Recommended"},
    "service": {"prefix": "dcat:service", "description": "Links to data services", "required": "Recommended"},
    "issued": {"prefix": "dct:issued", "description": "Catalog issue date", "required": "Recommended"},
    "modified": {"prefix": "dct:modified", "description": "Catalog last modified date", "required": "Recommended"},
    "themeTaxonomy": {"prefix": "dcat:themeTaxonomy", "description": "Controlled theme vocabulary", "required": "Recommended"},
    "record": {"prefix": "dcat:record", "description": "Metadata records included", "required": "Optional"},
    "language": {"prefix": "dct:language", "description": "Language of the catalog", "required": "Optional"},
    "license": {"prefix": "dct:license", "description": "License for the catalog", "required": "Optional"},
    "homepage": {"prefix": "foaf:homepage", "description": "Homepage URL", "required": "Optional"},
    "contactPoint": {"prefix": "dcat:contactPoint", "description": "Contact information", "required": "Optional"}
}

# DCAT 3 validation functions
def validate_required_fields(catalog_data):
    """Validate that all required fields are filled"""
    required_fields = []
    missing_fields = []
    
    for prop_name, prop in catalog_properties.items():
        if prop['required'] == 'Required':
            required_fields.append(prop_name)
            if not catalog_data.get(prop_name) or catalog_data[prop_name].strip() == "":
                missing_fields.append(prop_name)
    
    return missing_fields

def validate_url_fields(catalog_data):
    """Validate URL fields have proper format"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    url_fields = ['homepage']
    invalid_urls = []
    
    for field in url_fields:
        value = catalog_data.get(field, "")
        if value and not url_pattern.match(value):
            invalid_urls.append(field)
    
    return invalid_urls

def validate_date_fields(catalog_data):
    """Validate date fields have proper ISO format"""
    import re
    # ISO 8601 date pattern (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?$')
    
    date_fields = ['issued', 'modified']
    invalid_dates = []
    
    for field in date_fields:
        value = catalog_data.get(field, "")
        if value and not date_pattern.match(value):
            invalid_dates.append(field)
    
    return invalid_dates

def validate_dcat_compliance(catalog_data):
    """Comprehensive DCAT 3 validation"""
    validation_results = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'info': []
    }
    
    # Check required fields
    missing_required = validate_required_fields(catalog_data)
    if missing_required:
        validation_results['is_valid'] = False
        validation_results['errors'].append(f"Missing required fields: {', '.join(missing_required)}")
    
    # Check URL format
    invalid_urls = validate_url_fields(catalog_data)
    if invalid_urls:
        validation_results['warnings'].append(f"Invalid URL format in: {', '.join(invalid_urls)}")
    
    # Check date format
    invalid_dates = validate_date_fields(catalog_data)
    if invalid_dates:
        validation_results['warnings'].append(f"Invalid date format in: {', '.join(invalid_dates)} (use YYYY-MM-DD)")
    
    # Check recommended fields
    recommended_missing = []
    for prop_name, prop in catalog_properties.items():
        if prop['required'] == 'Recommended':
            if not catalog_data.get(prop_name) or catalog_data[prop_name].strip() == "":
                recommended_missing.append(prop_name)
    
    if recommended_missing:
        validation_results['warnings'].append(f"Missing recommended fields: {', '.join(recommended_missing)}")
    
    # Info about filled fields
    filled_fields = [name for name, value in catalog_data.items() if value and value.strip()]
    validation_results['info'].append(f"Filled fields: {len(filled_fields)}/{len(catalog_properties)}")
    
    return validation_results

def generate_rdf_turtle(catalog_data):
    """Generate RDF Turtle representation of the catalog data"""
    turtle_content = []
    
    # Add prefixes
    for prefix, uri in prefixes.items():
        turtle_content.append(f"@prefix {prefix}: <{uri}> .")
    
    turtle_content.append("")
    turtle_content.append("# DCAT Catalog")
    turtle_content.append("<http://example.org/catalog> a dcat:Catalog ;")
    
    # Add properties
    properties = []
    for prop_name, value in catalog_data.items():
        if value and value.strip():
            prop_info = catalog_properties[prop_name]
            prefix_prop = prop_info['prefix']
            
            # Handle different data types
            if prop_name in ['issued', 'modified']:
                # Date literals
                properties.append(f'    {prefix_prop} "{value}"^^xsd:date')
            elif prop_name == 'homepage':
                # URL as resource
                properties.append(f'    {prefix_prop} <{value}>')
            else:
                # String literals
                escaped_value = value.replace('"', '\\"')
                properties.append(f'    {prefix_prop} "{escaped_value}"')
    
    turtle_content.extend(properties)
    if properties:
        turtle_content[-1] += " ."
    else:
        turtle_content[-1] = turtle_content[-1].rstrip(' ;') + " ."
    
    return "\n".join(turtle_content)

def validate_shacl_constraints(catalog_data):
    """SHACL-style validation constraints for DCAT"""
    shacl_results = {
        'is_valid': True,
        'violations': [],
        'conforms': True
    }
    
    # SHACL Constraint 1: Catalog must have exactly one title
    title_values = [v for v in [catalog_data.get('title', '')] if v.strip()]
    if len(title_values) != 1:
        shacl_results['is_valid'] = False
        shacl_results['conforms'] = False
        shacl_results['violations'].append({
            'constraint': 'sh:minCount 1, sh:maxCount 1',
            'property': 'dct:title',
            'message': 'Catalog must have exactly one title',
            'severity': 'sh:Violation'
        })
    
    # SHACL Constraint 2: Description minimum length
    description = catalog_data.get('description', '')
    if description and len(description.strip()) < 10:
        shacl_results['violations'].append({
            'constraint': 'sh:minLength 10',
            'property': 'dct:description',
            'message': 'Description must be at least 10 characters long',
            'severity': 'sh:Warning'
        })
    
    # SHACL Constraint 3: Publisher must be non-empty string
    publisher = catalog_data.get('publisher', '')
    if publisher and not publisher.strip():
        shacl_results['is_valid'] = False
        shacl_results['conforms'] = False
        shacl_results['violations'].append({
            'constraint': 'sh:minLength 1',
            'property': 'dct:publisher',
            'message': 'Publisher cannot be empty string',
            'severity': 'sh:Violation'
        })
    
    # SHACL Constraint 4: Homepage must be valid IRI
    homepage = catalog_data.get('homepage', '')
    if homepage:
        import re
        iri_pattern = re.compile(r'^https?://[^\s]+$')
        if not iri_pattern.match(homepage):
            shacl_results['violations'].append({
                'constraint': 'sh:nodeKind sh:IRI',
                'property': 'foaf:homepage',
                'message': 'Homepage must be a valid IRI (URL)',
                'severity': 'sh:Warning'
            })
    
    # SHACL Constraint 5: Date format validation
    for date_field in ['issued', 'modified']:
        date_value = catalog_data.get(date_field, '')
        if date_value:
            import re
            date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
            if not date_pattern.match(date_value):
                shacl_results['violations'].append({
                    'constraint': 'sh:pattern "^\\\\d{4}-\\\\d{2}-\\\\d{2}$"',
                    'property': f'dct:{date_field}',
                    'message': f'{date_field.capitalize()} must follow YYYY-MM-DD format',
                    'severity': 'sh:Warning'
                })
    
    # SHACL Constraint 6: Language must be valid language tag
    language = catalog_data.get('language', '')
    if language:
        import re
        lang_pattern = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')  # e.g., "en", "en-US"
        if not lang_pattern.match(language):
            shacl_results['violations'].append({
                'constraint': 'sh:pattern "^[a-z]{2}(-[A-Z]{2})?$"',
                'property': 'dct:language',
                'message': 'Language must be a valid language tag (e.g., "en", "en-US")',
                'severity': 'sh:Warning'
            })
    
    return shacl_results


catalog_data = {}
# Create a form in Streamlit
with st.form("my_form"):
    st.markdown(f'<p><strong style="color:blue;">Create DCAT 3 Catgalog</strong></p>', unsafe_allow_html=True)
    with st.expander("Catalog Properties", expanded=False):
        for prop_name, prop in catalog_properties.items():
            if prop['required'] == "Required":
                color="red"
            elif prop['required'] == "Recommended":
                color="orange"
            else:   
                color="black"
            print(f"Property: {prop_name}, Required: {prop['required']}, Description: {prop['description']}")
            # Use st.html() with inline CSS for better control
            st.html(f'<div style="color:{color}; margin-bottom: -15px; font-size: 14px;"><strong>{prop_name}</strong> <em> <span style="opacity: 0.6;">({prop["required"]}) ({prop["description"]})</span></em></div>')
            value = st.text_input("", key=prop_name, label_visibility="collapsed")
            catalog_data[prop_name] = value
        validate_button = st.form_submit_button("Validate")
        
    if validate_button:
        st.success(f"Form VALIDATED successfully!")
        
        # Validate DCAT compliance
        validation = validate_dcat_compliance(catalog_data)
        
        # Validate SHACL constraints
        shacl_validation = validate_shacl_constraints(catalog_data)
        
        # Display validation results
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### DCAT 3 Basic Validation")
            if validation['is_valid']:
                st.success("✅ VALID")
            else:
                st.error("❌ INVALID")
        
        with col2:
            st.markdown("#### SHACL Constraints")
            if shacl_validation['conforms']:
                st.success("✅ CONFORMS")
            else:
                st.error("❌ VIOLATIONS")
        
        # Show DCAT errors
        if validation['errors']:
            st.error("**DCAT Errors:**")
            for error in validation['errors']:
                st.error(f"• {error}")
        
        # Show DCAT warnings
        if validation['warnings']:
            st.warning("**DCAT Warnings:**")
            for warning in validation['warnings']:
                st.warning(f"• {warning}")
        
        # Show SHACL violations
        if shacl_validation['violations']:
            st.markdown("#### SHACL Validation Report")
            for violation in shacl_validation['violations']:
                severity_color = "🔴" if violation['severity'] == 'sh:Violation' else "🟡"
                st.markdown(f"**{severity_color} {violation['property']}**")
                st.markdown(f"- **Constraint:** `{violation['constraint']}`")
                st.markdown(f"- **Message:** {violation['message']}")
                st.markdown("---")
        
        # Show info
        if validation['info']:
            for info in validation['info']:
                st.info(f"ℹ️ {info}")
        
        # Generate and display RDF
        with st.expander("View Generated RDF (Turtle)", expanded=False):
            rdf_turtle = generate_rdf_turtle(catalog_data)
            st.code(rdf_turtle, language="turtle")
        
        # Display form data
        with st.expander("View Submitted Data", expanded=True):
            st.markdown("### Submitted Data:")
            for prop_name, value in catalog_data.items():
                if value:  # Only show filled fields
                    prop_info = catalog_properties[prop_name]
                    st.write(f"**{prop_name}:** {value}")
                    st.caption(f"Property: {prop_info['prefix']} | Status: {prop_info['required']}")   

        # Write button functionality
        write = st.form_submit_button("Write Turtle File")
        
        if write:
            # Generate the RDF turtle content
            rdf_turtle = generate_rdf_turtle(catalog_data)
            print("TURTLE", rdf_turtle)
            # Create filename based on catalog title or use default
            catalog_title = catalog_data.get('title', 'catalog').strip()
            if catalog_title:
                # Clean filename - remove invalid characters
                import re
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', catalog_title)
                filename = f"{safe_filename}.ttl"
            else:
                filename = "dcat_catalog.ttl"
            
            # Write to file
            try:
                print(f"Writing RDF Turtle to file: {filename}")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(rdf_turtle)
                    f.close()
                # File is automatically closed when exiting the 'with' block
                st.success(f"✅ Turtle file written successfully: `{filename}`")
                
               
            except Exception as e:
                st.error(f"❌ Error writing file: {str(e)}")
                
                # Still provide download option even if file write fails
                
# Optional: Add some explanatory text
