/*
   Secretary Of State CSI Reg Finan ETL Script
   v1.0.0
   Last Modified: 2013-12-11
*/
require('dotenv').config({path: __dirname + '/home/joe/bic_etl/.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
const orr = require(path.resolve(path.join(process.env.bic_etl_home, 'cdos/business/nonprofit/scripts/orr.js')));
const orrc = orr({"state": "CO", "rulesPath": "/home/joe/bic_etl/cdos/business/nonprofit/scripts/rules/rules-sos-csi-reg-finan-principal.txt"});
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'reg_finan')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);


program.title = (program.title) ? program.title : 'reg finan';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
  log = custom_logger;
  try {
    initiate();
  } catch(e) {
    log.error("Unhandled error: " + e);
    process.exit();
  }
})

function initiate() {
  log.debug("Program Started");

  let ext = (program.ext) ? program.ext : '.tsv';
  let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source','OLD', 'reg_finan.tsv');
  file_path = path.resolve(file_path);

  let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'reg_finan_test.csv');

  if (!fs.existsSync(file_path)) {
    log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
      return;
  }

  transform_reg_finan(file_path, outfile); // Executes the processing
}

let header_columns = [
  "entityId",
  "registrantTypeAbbr",
  "name",
  "fein",
  "filingType",
  "documentId",
  "amendmentEntityId",
  //"externalFilingFromNccs",
  //"externalFilingType",
  "actualFinancialsProvided",
  "principalAddress",
  "principalAddress2",
  "principalCity",
  "principalState",
  "principalProvince",
  "residentialCounty",
  "principalCountry",
  "principalZipcode",
  "principalZipcode4",
  "mailingAddress",
  "mailingAddress2",
  "mailingCity",
  "mailingState",
  "mailingProvince",
  "mailingZipcode",
  "mailingZipcode4",
  "mailingCountry",
  "phone",
  "fax",
  "website",
  "authorizedOfficerName",
  "authorizedOfficerSignedDate",
  "cfoName",
  "cfoSignedDate",
  "registrationApprovedDate",
  "paymentProcessedDate",
  "nextRenewalRegistrationDate",
  // "fiscalYearStartDate",
  "fiscalYearStartDate",
  "fiscalYearEndDate",
  // "fiscalYearEndDate",
  // "incorporated",
  // "incorporationDate",
  // "incorporationState",
  // "organizationEstablishedDate",
  // "organizationEstablishedState",
  "NTEECode1",
  "NTEECode2",
  "NTEECode3",
  // "legalEntityType",
  "taxExemptStatus",
  "taxExemptCode",
  "IRSDeterminationDate",
  "donationsTaxDeductible",
  "extensionFiled",
  "consolidatedRegistrationStatement",
  "publicBenefitCorporation",
  "reportingPeriodBegin",
  "reportingPeriodEnd",
  //"newCharity",
  "outsideProfessionalFundraiserFees",
  "totalContributionsRaisedPreviousYear",
  "totalFundraisingExpensesPreviousYear",
  "totalManagementGeneralExpensesPreviousYear",
  "expensesDividedByContributions",
  "totalExpensesPlusManagementGeneralDividedByContributions",
  "relatedOrganizationName",
  "relatedToOtherOrganization",
  "relatedOrganizationTaxExempt",
  "solicitedNonTaxDeductibleGifts",
  "statedGiftNotTaxDeductible",
  "pbcRecordingMethod",
  "pbcPromotedBenifit",
  //"pbcIssuesStockShares",
  //"pbcStockSharesAvailable",
  "pbcBenefitReportSent",
  "pbcAnnualBenefitReport",
  "revenueFromContibutions",
  "revenueFromGovernment",
  "programServiceRevenue",
  "revenueFromInvestments",
  "revenueFromSpecialEvents",
  "revenueFromSales",
  "revenueFromOther",
  //"revenueOther",
  "revenueTotal",
  "expensesFromProgramServices",
  "expensesFromAdministrativeOther",
  "expensesFundraising",
  "expensesAffiliates",
  "expensesOther",
  "expensesOtherComment",
  "expensesTotal",
  "endOfYearAssests",
  "endOfYearTotalLiabilities",
  "endOfYearAssestsMinusLiabilities",
  "unrestrictedAssests",
  "temporarilyRestrictedAssets",
  "permanentlyRestrictedAssets",
  "conflictOfInterest",
  "conflictOfInterestAffirmation",
  "legalBusinessFormation",
  "placeFormed",
  "dateFormed",
  "currentStatus",
  "statusDate",
  "expirationDate",
  "programServiceRatio"
];

const ynMap = { "y": 1,"n": 0 };
/*
 * added column names
 * normalized phone and fax numbers
 * normalized website urls
 * fixed capitals on names
 * converted dates to 'ISO'
 */
function transformation(row) {

  let entity_id_input = 'Entity Id';
  for(let key in row) {
    if(key.indexOf('Entity Id') > -1) {
      entity_id_input = key;
    }
  }
  let urlRegex = /^[-a-zA-Z0-9:%_\+.~#?&//=]{2,256}\.[a-z]{2,4}\b(\/[-a-zA-Z0-9:%_\+.~#?&//=]*)?/gi;

	let tmpTest = /temp/gi;
  let tRow                                                         = {};
  tRow["entityId"]                                                 = row[entity_id_input];
  tRow["registrantTypeAbbr"]                                       = row['Entity Type'];
  tRow["name"]                                                     = row['Org Name'];
  tRow["fein"]                                                     = row['Ce Fein'].replace(/-/g, '');
  tRow["filingType"]                                               = row['Filing Type'];
  // Ignore Filing Status
  tRow["documentId"]                                               = row['Document Id'];
  tRow["amendmentEntityId"]                                        = row['Ce Parent Id'];
  //tRow["externalFilingFromNccs"]                                   = row['Ce Ext Filing Flg'] ? ynMap[row['Ce Ext Filing Flg'].toLowerCase()] : null;
 // tRow["externalFilingType"]                                       = row['Ce External Typ'];
  tRow["actualFinancialsProvided"]                                 = row['Ce Actual Flg'] ? ynMap[row['Ce Actual Flg'].toLowerCase()] :null;
  // Ignore Ce Vchr Num
  tRow["principalAddress"]                                         = row['Ce Paddr'];
  tRow["principalAddress2"]                                        = row["Ce Paddr2"];
  tRow["principalCity"]                                            = orrc.resolve(custom_helper.fixCap(row['Ce Pcity']), row['Ce Pcity']);
  tRow["principalState"]                                           = row['Ce Pstate'];
  tRow["principalProvince"]                                        = row['Ce Province'];
  tRow["residentialCounty"]                                        = row['Ce Cnty'];
  tRow["principalCountry"]                                         = row['Ce Country'];
  tRow["principalZipcode"]                                         = custom_helper.getZipBase(row['Ce Pzip']);
  tRow["principalZipcode4"]                                        = custom_helper.getZip4(row['Ce Pzip']);
  tRow["mailingAddress"]                                           = row['Ce Maddr'];
  tRow["mailingAddress2"]                                          = row['Ce Maddr2'];
  tRow["mailingCity"]                                              = row['Ce Mcity'];
  tRow["mailingState"]                                             = row['Ce Mstate'];
  tRow["mailingProvince"]                                          = row['Ce Mprovince'];
  tRow["mailingZipcode"]                                           = custom_helper.getZipBase(row['Ce Mail Zip']);
  tRow["mailingZipcode4"]                                          = custom_helper.getZip4(row['Ce Mail Zip']);
  tRow["mailingCountry"]                                           = row['Ce Mcountry'];
  tRow["phone"]                                                    = custom_helper.fixPhoneNumber(row['Ce Phone']);
  tRow["fax"]                                                      = custom_helper.fixPhoneNumber(row['Ce Fax']);
  tRow["website"]                                                  = (urlRegex.exec(row['Ce Url'].toLowerCase())) ? row['Ce Url'].toLowerCase().replace(/.*?:\/\//g, "") : "";
  tRow["authorizedOfficerName"]                                    = custom_helper.fixCap(row['Ce A1sign']);
  tRow["authorizedOfficerSignedDate"]                              = moment(row['Ce A1sign Date'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["cfoName"]                                                  = custom_helper.fixCap(row['Ce A2sign']);
  tRow["cfoSignedDate"]                                            = moment(row['Ce A2sign Date'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["registrationApprovedDate"]                                 = moment(row['Ce File Date'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["paymentProcessedDate"]                                     = moment(row['Ce Date Paid'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["nextRenewalRegistrationDate"]                              = moment(row['Ce Renew Due'], 'YYYY/MM/DD').format('MM/DD/YYYY').replace("Invalid date", "");
  
  // tRow["fiscalYearStartDate"]                                      = moment(row['Ce Org Fy Start'], 'MM/DD/YY hh:mm a').format('MM/DD/YYYY hh:mm:ss a').replace("Invalid date", "");
  tRow["fiscalYearStartDate"]                                      = row['Ce Org Fy Start']
  
  // tRow["fiscalYearEndDate"]                                        = moment(row['Ce Org Fy Ends'], 'MM/DD/YY hh:mm a').format('MM/DD/YYYY hh:mm:ss a').replace("Invalid date", "");
  tRow["fiscalYearEndDate"]                                        = row['Ce Org Fy Ends']
 
  // tRow["incorporated"]                                             = row['Ce Inc Flg'] ? ynMap[row['Ce Inc Flg'].toLowerCase()] : null;
  // tRow["incorporationDate"]                                        = moment(row['Ce Org Date Inc'], 'YYYY/MM/DD').format('MM/DD/YYYY').replace("Invalid date", "");
  // tRow["incorporationState"]                                       = row['Ce Org State Inc'];
  // tRow["organizationEstablishedDate"]                              = moment(row['Ce Date Est'], 'YYYY/MM/DD').format('MM/DD/YYYY').replace("Invalid date", "");
  // tRow["organizationEstablishedState"]                             = row['Ce State Est'];
  tRow["NTEECode1"]                                                = row['Ntee Dscrp'];
  tRow["NTEECode2"]                                                = row['Ntee Dscrp2'];
  tRow["NTEECode3"]                                                = row['Ntee Dscrp3'];
    // tRow["legalEntityType"]                                          = row['Ce Type'];
  tRow["taxExemptStatus"]                                          = row['Ce Org Txmpt Flg'] ? ynMap[row['Ce Org Txmpt Flg'].toLowerCase()] : null;
  tRow["taxExemptCode"]                                            = row['Ce Org Txmpt Code'];
  tRow["IRSDeterminationDate"]                                         = moment(row['Ce Org Txmpt Date'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["donationsTaxDeductible"]                                            = row['Ce Org Txdduc Flg'] ? ynMap[row['Ce Org Txdduc Flg'].toLowerCase()]: null;
  tRow["extensionFiled"]                                           = row['Ce Ext Flg'] ? ynMap[row['Ce Ext Flg'].toLowerCase()] : null;
  tRow["consolidatedRegistrationStatement"]                        = row['Ce Cons Flg'] ? ynMap[row['Ce Cons Flg'].toLowerCase()]: null;
  tRow["publicBenefitCorporation"]				                         = row['Ce Pbc Flg'] ? ynMap[row['Ce Pbc Flg'].toLowerCase()]: null;
  tRow["reportingPeriodBegin"]                                      = moment(row['Of Begin Taxyr'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["reportingPeriodEnd"]                                         = moment(row['Of Endng Taxyr'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
 // tRow["newCharity"]                                               = row['Of Est Flg'] ? ynMap[row['Of Est Flg'].toLowerCase()] : null;
  tRow["outsideProfessionalFundraiserFees"]                        = row['Of Pf Fees'].replace(/,/g,"");
  tRow["totalContributionsRaisedPreviousYear"]                     = row['Of Py Cntrbs'].replace(/,/g,"");
  tRow["totalFundraisingExpensesPreviousYear"]                     = row['Of Py Frcosts'].replace(/,/g,"");
  tRow["totalManagementGeneralExpensesPreviousYear"]               = row['Of Py Mcosts'].replace(/,/g,"");
  tRow["expensesDividedByContributions"]                           = row['Of Fr Prcnt1'];
  tRow["totalExpensesPlusManagementGeneralDividedByContributions"] = row['Of Fr Prcnt2'];
  tRow["relatedOrganizationName"]                                     = row['Of Oorg Name'];
  tRow["relatedToOtherOrganization"]                               = row['Of Oorg Flg'] ? ynMap[row['Of Oorg Flg'].toLowerCase()] : null;
  tRow["relatedOrganizationTaxExempt"]                             = row['Of Exoorg Flg'] ? ynMap[row['Of Exoorg Flg'].toLowerCase()] : null;
  tRow["solicitedNonTaxDeductibleGifts"]                           = row['Of Txddct Flg'] ? ynMap[row['Of Txddct Flg'].toLowerCase()] : null;
  tRow["statedGiftNotTaxDeductible"]                               = row['Of Txstmt Flg'] ? ynMap[row['Of Txstmt Flg'].toLowerCase()] : null;
  tRow["pbcRecordingMethod"]					                             = row['Of Pbc Method'];
  tRow["pbcPromotedBenifit"]					                             = row['Of Pbc Promo'];
  //tRow["pbcIssuesStockShares"]				                             = row['Of Pbc Shr Flg'] ? ynMap[row['Of Pbc Shr Flg'].toLowerCase()] : null;
  //tRow["pbcStockSharesAvailable"]				                           = row['Of Pbc Shr Num'];
  tRow["pbcBenefitReportSent"]				                             = row['Of Pbc Rpt Sent'];
  tRow["pbcAnnualBenefitReport"]				                           = row['Of Pbc Location'];
  tRow["revenueFromContibutions"]                                  = row['Os Rev Cntrb'].replace(/,/g,"");
  tRow["revenueFromGovernment"]                                    = row['Os Rev Grnts'].replace(/,/g,"");
  tRow["programServiceRevenue"]                                    = row['Os Rev Pserv'].replace(/,/g,"");
  tRow["revenueFromInvestments"]                                   = row['Os Rev Inv'].replace(/,/g,"");
  tRow["revenueFromSpecialEvents"]                                 = row['Os Rev Evnts'].replace(/,/g,"");
  tRow["revenueFromSales"]                                         = row['Os Rev Sales'].replace(/,/g,"");
  tRow["revenueFromOther"]                                         = row['Os Rev Othr'].replace(/,/g,"");
  //tRow["revenueOther"]                                             = row['Os Exp Othr'].replace(/,/g,"");
  tRow["revenueTotal"]                                             = row['Os Tot Rev'].replace(/,/g,"");
  tRow["expensesFromProgramServices"]                              = row['Os Exp Pserv'].replace(/,/g,"");
  tRow["expensesFromAdministrativeOther"]                          = row['Os Exp Admn'].replace(/,/g,"");
  tRow["expensesFundraising"]                                      = row['Os Exp Fundr'].replace(/,/g,"");
  tRow["expensesAffiliates"]                                       = row['Os Exp Payaff'].replace(/,/g,"");
  tRow["expensesOther"]                                            = row['Os Exp Othr'].replace(/,/g,"");
  tRow["expensesOtherComment"]                                     = row['Os Exp Comment']; //
  tRow["expensesTotal"]                                            = row['Os Tot Exp'].replace(/,/g,"");
  tRow["endOfYearAssests"]                                         = row['Os Eoy Ass'].replace(/,/g,"");
  tRow["endOfYearTotalLiabilities"]                                = row['Os Eoy Liab'].replace(/,/g,"");
  tRow["endOfYearAssestsMinusLiabilities"]                         = row['Os Net Ass'].replace(/,/g,"");
  tRow["unrestrictedAssests"]                                      = row['Os Unrstr Ass'].replace(/,/g,"");
  tRow["temporarilyRestrictedAssets"]                             = row['Os Temp Ass'].replace(/,/g,"");
  tRow["permanentlyRestrictedAssets"]                              = row['Os Perm Ass'].replace(/,/g,"");
  tRow["conflictOfInterest"]					                             = row['Ce Ps Coi Flg'] ? ynMap[row['Ce Ps Coi Flg'].toLowerCase()]: null;
  tRow["conflictOfInterestAffirmation"]		            	           = row['Ce Ps Coi Affirm'] ? ynMap[row['Ce Ps Coi Affirm'].toLowerCase()] : null;
  tRow["legalBusinessFormation"]				                           = row['Legal Form'];
  tRow["placeFormed"]                                              = row['Place Formed'];
  tRow["dateFormed"]                                               = row['Date Formed'];
  tRow["currentStatus"]                                            = row['Current Status'];
  //tRow["statusDate"]                                               = row['Status Date'];
  tRow["statusDate"]                                         = moment(row['Status Date'], 'YYYYMMDD').format('MM/DD/YYYY').replace("Invalid date", "");
  tRow["expirationDate"]                                           = row['Expiration Date'];
  tRow["programServiceRatio"]                                      = row['Program Services Ratio'];
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
function transform_reg_finan(file_path, outfile) {
  log.debug("Files to be transformed: " + file_path);
  //Original file
  let input_stream = fs.createReadStream(file_path)
  .on('error', error_handler);
  //Transformed file
  let output_stream = fs.createWriteStream(outfile)
  .on('error', error_handler);
  //Parse input
  let reg_finan_parser = parse({
      relax: true,
      delimiter: "\t",
      columns: true
  })
  .on('error', error_handler);
  //Transform input
  let reg_finan_transformer = transform(transformation)
  .on('error', error_handler);
  //New data to output
  let reg_finan_stringifier = stringify({
      header: true,
      columns: header_columns
  })
  .on('error', error_handler);
  // Connect all streams
  input_stream.pipe(reg_finan_parser).pipe(reg_finan_transformer).pipe(reg_finan_stringifier).pipe(output_stream);

  //Once complete
  output_stream.on('finish', function() {
      log.debug('All items have been processed, final file is at: '+ outfile);
  });
}