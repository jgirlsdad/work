require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const moment = require('moment');

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'purpose')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'purpose';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'purpose.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'purpose.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_purpose(file_path, outfile); // Executes the processing
}

let header_columns = [
    "entityId",
    "documentId",
    "fein",
    "name",
    "statementOfPurpose",
    "filingDate"
];

/*
 */
function transformation(row) {
  let entity_id_input = 'Entity Id';
  for(let key in row) {
    if(key.indexOf('Entity Id') > -1) {
      entity_id_input = key;
    }
  }

    let tRow                   = {};
    tRow["entityId"]           = row[entity_id_input];
    tRow["documentId"]             = row["Document Id"];
    tRow["fein"]               = row["Ce Fein"].replace(/-/g, '');
    tRow["name"]               = row["Org Name"];
    tRow["statementOfPurpose"] = row["Cr Purpose"];
    tRow["filingDate"]         = moment(row['Ce File Date'], 'MM/DD/YYYY hh:mm a').format('MM/DD/YYYY').replace('Invalid date', '');
  
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
function transform_purpose(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const purpose_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const purpose_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const purpose_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(purpose_parser).pipe(purpose_transformer).pipe(purpose_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}