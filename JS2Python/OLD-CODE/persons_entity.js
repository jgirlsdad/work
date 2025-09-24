require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
const orr = require(path.resolve(path.join(process.env.bic_etl_home, 'cdos/business/nonprofit/scripts/orr.js')));
const orrc = orr({"state": "CO", "rulesPath": __dirname + "/rules/rules-sos-csi-persons-entity-principal.txt"});
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'persons_entity')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'persons_entity';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'persons_entity.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'persons_entity.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_persons_entity(file_path, outfile); // Executes the processing
}

let txtFileName = 'persons_entity.txt';
let ynMap = { "y": 1, "n": 0 };


let header_columns = [
    "entityId",
    "entityType",
    "documentId",
    "fein",
    "name",
    "title",
    "businessName",
    "firstName",
    "middleName",
    "lastName",
    "principalAddress",
    "principalCity",
    "principalState",
    "principalZipCode",
    "principalZipCode4",
    "mailingAddress",
    "mailingCity",
    "mailingState",
    "mailingZipCode",
    "mailingZipCode4",
    "phone",
    "subcontractor",
    "inBusiness"
];

/*
 * added column names
 * camel cased names and cities
 * normalized phonenumbers
 * removed violation and organization columns
 * removed any "N/A", "NONE", or "UKNOWN" values
*/
function transformation(row) {
  let entity_id_input = 'Entity Id';
  for(let key in row) {
    if(key.indexOf('Entity Id') > -1) {
      entity_id_input = key;
    }
  }

    let tRow                  = {};
    tRow["entityId"]          = row[entity_id_input];
    tRow["entityType"]        = row["Entity Type"];
    tRow["documentId"]        = row["Document Id"]
    tRow["fein"]              = row["Ce Fein"].replace(/-/g, '');
    tRow["name"]              = row["Org Name"];
    tRow["title"]             = row["Cp Title"];
    tRow["businessName"]      = row["Cp Bsn Name"];
    tRow["firstName"]         = custom_helper.fixCap(row["Cp Fname"]);
    tRow["middleName"]        = custom_helper.fixCap(row["Cp Mname"]);
    tRow["lastName"]          = custom_helper.fixCap(row["Cp Lname"]);
    tRow["principalAddress"]  = row["Address"];
    tRow["principalCity"]     = orrc.resolve(row["City"], row["State"]);
    tRow["principalState"]    = row["State"];
    tRow["principalZipCode"]  = custom_helper.getZipBase(row["Zip"]);
    tRow["principalZipCode4"] = custom_helper.getZip4(row["Zip"]);
    tRow["mailingAddress"]    = row["M Address"];
    tRow["mailingCity"]       = row["M City"];
    tRow["mailingState"]      = row["M State"];
    tRow["mailingZipCode"]    = custom_helper.getZipBase(row["M Zip"]);
    tRow["mailingZipCode4"]   = custom_helper.getZip4(row["M Zip"]);
    tRow["phone"]             = custom_helper.fixPhoneNumber(row["Cp Phone"]);
    tRow["subcontractor"]     = ynMap[row["Cp Subc Flg"].toLowerCase()];
    tRow["inBusiness"]        = ynMap[row["Cp Sol Offcr Flg"].toLowerCase()];
    return tRow;
}

function error_handler(e) {
    log.error("Error mid-stream: " + e);
    setTimeout(function() {
      process.exit(1);
    }, 200);
}

/*
   This function will get the files to be transformed and perform the transform
*/
function transform_persons_entity(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const persons_entity_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const persons_entity_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const persons_entity_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(persons_entity_parser).pipe(persons_entity_transformer).pipe(persons_entity_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}
