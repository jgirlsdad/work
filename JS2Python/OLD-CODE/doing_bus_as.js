require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'doing_bus_as')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'doing_bus_as';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'doing_bus_as.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'doing_bus_as.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_doing_bus_as(file_path, outfile); // Executes the processing
}

let txtFileName = 'doing_bus_as.txt';
let ynMap = { "y": 1, "n": 0 };
let personTypeObj = {
    "PS": "Paid Solicitor",
    "PFC": "Professional Fundraising Consultant"
}

let header_columns = [
    "entityId",
    "documentId",
    "fein",
    "name",
    "otherName",
];

/*
 * added column names
 */
function transformation(row) {
//Entity Id	Ce Fein	Org Name	Sol Type Dscrp
  let entity_col_name = 'Entity Id';
  for(var key in row) {
    if(key.indexOf(entity_col_name) > -1) {
      entity_col_name = key;
    }
  }
  let tRow          = {};
  tRow["entityId"]  = row[entity_col_name];
  tRow["documentId"]      = row['Document Id'];
  tRow["fein"]      = row['Ce Fein'].replace(/-/g, '');
  tRow["name"]      = row['Org Name'];
  tRow["otherName"] = row['Cd Dba'];
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
function transform_doing_bus_as(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const doing_bus_as_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const doing_bus_as_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const doing_bus_as_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(doing_bus_as_parser).pipe(doing_bus_as_transformer).pipe(doing_bus_as_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}