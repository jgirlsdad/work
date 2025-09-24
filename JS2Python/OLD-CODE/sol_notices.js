require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));
const moment = require('moment');

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'sol_notices')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'sol_notices';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'sol_ntcs.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'sol_notices.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_sol_notices(file_path, outfile); // Executes the processing
}

var ynMap = { "y": 1,"n": 0};

var header_columns = [
    "solicitationNoticeId",
    "charityName",
    "charityEntityID",
    "solicitorName",
    "paidSolicitorEntityId",
    "filingType",
    "documentId",
    "amendmentDocumentID",
    "solicitationApprovedDate",
    "paymentProcessedDate",
    "campaignCommencementDate",
    "campaignConclusionDate",
    "charityOfficerName",
    "charitySignedDate",
    "custodyOfContributions",
    "custodyOfFinancialRecords",
    "eventCampaignDescription",
    "accountingRecordsAddress",
    "accountingRecordsCity",
    "accountingRecordsState",
    "accountingRecordsZipCode",
    // "financialInstitutionDeposits",
    // "financialInstitutionAddress",
    // "financialInstitutionCity",
    // "financialInstitutionState",
    // "financialInstitutionZipCode",
    "charityControlsFunds",
    // "financialInstitutionEntityId",
    "contractEffectiveDate",
    "contractTerminationDate",
    "percentageBasedContract",
    "minimumPercentageOfGrossReceiptsRemitted",
    "percentageEventPriceRemitted",
    "minimumPercentageSaleRemitted",
    "specifiedPercentageGrossRevenueReceivedBySolicitor",
    "solicitorCompensationPercentageBased",
    "estimatedPercentofGrossRevenue",
    "campaignPurpose",
    "respectiveObligations",
    "solicitorCompensationAssumptions",
    "contractSigner1FirstName",
    "contractSigner1LastName",
    "contractSigner1Title",
    "contractSigner1Organization",
    "contractSigner2FirstName",
    "contractSigner2LastName",
    "contractSigner2Title",
    "contractSigner2Organization",
    "contractSigner3FirstName",
    "contractSigner3LastName",
    "contractSigner3Title",
    "contractSigner3Organization",
    "contractSigner4FirstName",
    "contractSigner4LastName",
    "contractSigner4Title",
    "contractSigner4Organization"
];

/*
 * added column names
 * removed any "N/A", "NONE", or "UNKNOWN" values
 * Fixed capitalization on signer names at end of doc.
 * added zipcode 4 columns
 * changed dates to ISO format
 * changed "Y" and "N" columns to integers(1 and 0)
 */
function transformation(row) {
	let sol_notice_key = 'Sols Notice Id';
  for(let key in row) {
    if(key.indexOf(sol_notice_key) > -1) {
      sol_notice_key = key;
    }
  }
	if (row[sol_notice_key] == "") return null;

    var tRow                                                   = {};
    tRow["solicitationNoticeId"]                               = row[sol_notice_key];
    tRow["charityName"]                                        = row['Ce Name'];
    tRow["charityEntityID"]                                    = row['Entity Id Org'];
    tRow["solicitorName"]                                      = row['PS Name'];
    tRow["paidSolicitorEntityId"]                              = row['Entity Id Sol'];
    tRow["filingType"]                                         = row['Filing Type'];
    tRow["documentId"]                                         = row['Sn Acct Id'];
    tRow["amendmentDocumentID"]                                  = row['Sn Parent Id'];
    tRow["solicitationApprovedDate"]                           = (row['Sn File Date'] != "" && typeof row['Sn File Date'] !== 'undefined') ? moment(row['Sn File Date'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";
    tRow["paymentProcessedDate"]                               = (row['Sn Date Paid'] != "" && typeof row['Sn Date Paid'] !== 'undefined') ? moment(row['Sn Date Paid'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";
    tRow["campaignCommencementDate"]                           = (row['Sn Comm Date'] != "" && typeof row['Sn Comm Date'] !== 'undefined') ? moment(row['Sn Comm Date'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";
    tRow["campaignConclusionDate"]                             = (row['Sn Cncl Date'] != "" && typeof row['Sn Cncl Date'] !== 'undefined') ? moment(row['Sn Cncl Date'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";
    tRow["charityOfficerName"]                                 = row['Org Offcl'];
    tRow["charitySignedDate"]                                  = (row['Sn Cosign Date'] != "" && typeof row['Sn Cosign Date'] !== 'undefined') ? moment(row['Sn Cosign Date'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";
    tRow["custodyOfContributions"]                             = row['Sn Cntrb Flg'] ? ynMap[row['Sn Cntrb Flg'].toLowerCase()] : "";
    tRow["custodyOfFinancialRecords"]                          = row['Sn Frec Flg'] ? ynMap[row['Sn Frec Flg'].toLowerCase()] : "";
    tRow["eventCampaignDescription"]                           = row['Sn Evnt Dscrp'];
    tRow["accountingRecordsAddress"]                           = row['Sn Raddr'];
    tRow["accountingRecordsCity"]                              = row['Sn Rcity'];
    tRow["accountingRecordsState"]                             = row['Sn Rstate'];
    tRow["accountingRecordsZipCode"]                           = row['Sn Rzip'];
    // tRow["financialInstitutionDeposits"]                       = row['Sn Fi Name'];
    // tRow["financialInstitutionAddress"]                        = row['Sn Fiaddr'];
    // tRow["financialInstitutionCity"]                           = row['Sn Ficity'];
    // tRow["financialInstitutionState"]                          = row['Sn Fistate'];
    // tRow["financialInstitutionZipCode"]                        = row['Sn Fizip'];
    tRow["charityControlsFunds"]                    = row['Sn Co Cntrl Flg'] ? ynMap[row['Sn Co Cntrl Flg'].toLowerCase()] : "";
    tRow["contractEffectiveDate"]                              = (row['Nc Eff Date'] != "" && typeof row['Nc Eff Date'] !== 'undefined') ? moment(row['Nc Eff Date'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";
    tRow["contractTerminationDate"]                            = (row['Nc Term Date'] != "" && typeof row['Nc Term Date'] !== 'undefined') ? moment(row['Nc Term Date'], 'YYYYMMDD').format('YYYY-MM-DD').replace("Invalid date", "") : "";

    tRow["percentageBasedContract"]                            = row['Sn Co Cntrl Flg'] ? ynMap[row['Sn Co Cntrl Flg'].toLowerCase()] : "";

    tRow["minimumPercentageOfGrossReceiptsRemitted"]           = row['Nc Grecpts Prcnt'] ? row['Nc Grecpts Prcnt'].replace(/[A-Za-z]+|\W/g, '') : "";
    tRow["percentageEventPriceRemitted"]                       = row['Nc Sale Flg'] ? ynMap[row['Nc Sale Flg'].toLowerCase()] : "";
    tRow["minimumPercentageSaleRemitted"]                      = row['Nc Sale Prcnt'] ? row['Nc Sale Prcnt'].replace(/|[A-Za-z]+|\W/g, '') : "";
    tRow["specifiedPercentageGrossRevenueReceivedBySolicitor"] = row['Nc Grev Prcnt'] ? row['Nc Grev Prcnt'].replace(/[A-Za-z]+|\W/g, '') : "";
    tRow["solicitorCompensationPercentageBased"]  = row['Nc Pscomp Flg'] ? ynMap[row['Nc Pscomp Flg'].toLowerCase()] : "";
    tRow["estimatedPercentofGrossRevenue"]    = row['Nc Pscomp Prcnt'] ? row['Nc Pscomp Prcnt'].replace(/[A-Za-z]+|\W/g, '') : "";
    tRow["campaignPurpose"]                                    = row['Nc Purpose'];
    tRow["respectiveObligations"]                              = row['Nc Oblg Stmt'];
    tRow["solicitorCompensationAssumptions"]                   = row['Nc Assmp Stmt'];
    tRow["contractSigner1FirstName"]                           = row['Nc Fname1'] ? custom_helper.fixCap(row['Nc Fname1']) : "";
    tRow["contractSigner1LastName"]                            = row['Nc Lname1'] ? custom_helper.fixCap(row['Nc Lname1']) : "";
    tRow["contractSigner1Title"]                               = row['Nc Title1'];
    tRow["contractSigner1Organization"]                        = row['Nc Org1'];
    tRow["contractSigner2FirstName"]                           = row['Nc Fname2'] ? custom_helper.fixCap(row['Nc Fname2']) : "";
    tRow["contractSigner2LastName"]                            = row['Nc Lname2'] ? custom_helper.fixCap(row['Nc Lname2']) : "";
    tRow["contractSigner2Title"]                               = row['Nc Title2'];
    tRow["contractSigner2Organization"]                        = row['Nc Org2'];
    tRow["contractSigner3FirstName"]                           = row['Nc Fname3'] ? custom_helper.fixCap(row['Nc Fname3']) : "";
    tRow["contractSigner3LastName"]                            = row['Nc Lname3'] ? custom_helper.fixCap(row['Nc Lname3']) : "";
    tRow["contractSigner3Title"]                               = row['Nc Title3'];
    tRow["contractSigner3Organization"]                        = row['Nc Org3'];
    tRow["contractSigner4FirstName"]                           = row['Nc Fname4'] ? custom_helper.fixCap(row['Nc Fname4']) : "";
    tRow["contractSigner4LastName"]                            = row['Nc Lname4'] ? custom_helper.fixCap(row['Nc Lname4']) : "";
    tRow["contractSigner4Title"]                               = row['Nc Title4'];
    tRow["contractSigner4Organization"]                        = row['Nc Org4'];
    // console.log("ROW ",row)
    // console.log("TROW ",tRow)

    return tRow;
}


function error_handler(e) {
    log.error("Error mid-stream: " + e);
    log.error("Error mid-stream: " + e.stack);

    setTimeout(function() {
      process.exit(1);
    }, 200);
}

/*
   This function will get the files to be transformed and perform the transform
*/
function transform_sol_notices(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const sol_notices_parser = parse({
        relax: true,
        quote: '',
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const sol_notices_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const sol_notices_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(sol_notices_parser).pipe(sol_notices_transformer).pipe(sol_notices_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}
