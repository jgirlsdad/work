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
  .option('-t, --title <n>', 'sol_typ_entity')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'sol_typ_entity';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
  log = custom_logger;
  initiate();
});

const file_names = ['sol_typ_entity.tsv', 'sol_typ_sol_ntcs.tsv'];
let type_flag = 0;

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';

    for(let i=0; i< file_names.length; i++) {
      file_names[i] = path.join(process.env.bic_etl_home, 'cdos/business/nonprofit/data_source/', file_names[i]);
      if (!fs.existsSync(file_names[i])) {
        log.error("Folder " + file_names[i] + " does not exist to load TSV files for transform.");
          return;
      }
    }

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'sol_typ_entity.csv');

    transform_sol_typ_entity(file_names[0], outfile);
}




let header_columns = [
    "entityId",
    "fein",
    "name",
    "communicationType",
    "solicitationNotice"
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

    var tRow                   = {};
    tRow["entityId"]           = row[entity_id_input];
    tRow["fein"]               = row['Ce Fein'].replace(/-/g, '');
    tRow["name"]               = row['Org Name'];
    tRow["communicationType"]  = row['Sol Type Dscrp'];
    tRow["solicitationNotice"] = type_flag;
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
function transform_sol_typ_entity(file_path, outfile, append) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = null;
    if(append) {
      output_stream = fs.createWriteStream(outfile, {flag:'a'})
      .on('error', error_handler);
    } else {
      output_stream = fs.createWriteStream(outfile)
      .on('error', error_handler);
    }

    //Parse input
    const sol_typ_entity_parser = parse({
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const sol_typ_entity_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const sol_typ_entity_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(sol_typ_entity_parser).pipe(sol_typ_entity_transformer).pipe(sol_typ_entity_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed from ' + file_path + ', final file is at: '+ outfile);
        file_names.shift();
        type_flag = 1;
        if(file_names.length > 0) {
          transform_sol_typ_entity(file_names[0], outfile, 'append');
        }
    });
}