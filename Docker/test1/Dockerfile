FROM nikolaik/python-nodejs:python3.12-nodejs20-bullseye

RUN apt-get update 
RUN apt-get install -y --no-install-recommends ca-certificates curl
RUN curl -L -o openjdk.tar.gz https://download.java.net/java/GA/jdk11/13/GPL/openjdk-11.0.1_linux-x64_bin.tar.gz 
RUN mkdir jdk
RUN tar zxf openjdk.tar.gz -C jdk --strip-components=1 
RUN jdk/bin/java --version

# intall node dependencies
WORKDIR /usr/app
# COPY ./ ./
#RUN COPY /home/joe/.bashrc ./
#RUN source /usr/app/.bashrc
ENV PATH=/jdk/bin:$PATH
#RUN /jdk/bin/java --version
#-jar /home/joe/bic_etl/general/datasync/DataSync-1.8.2.jar -t LoadPreferences -c /home/joe/bic_etl/general/datasync/config.json
# Install base dependencies
# RUN npm install underscore -g
# RUN npm install moment -g
# RUN npm install dotenv -g
# RUN npm install path -g
# RUN npm install commander -g
# RUN npm install csv-parse -g
# RUN npm install stream-transform -g
# RUN npm install csv-stringify -g
# RUN npm install fs -g
#RUN /usr/bin/node /home/joe/bic_etl/general/scripts/bic_etl.js -p cdos/business/nonprofit -t  "Federal Tax-Exempt Subsection Codes in Colorado"
#CMD  ["/usr/bin/node --version"]

#CMD java -jar /home/joe/bic_etl/general/datasync/DataSync-1.8.2.jar -t LoadPreferences -c /home/joe/bic_etl/general/datasync/config.json; node  /home/joe/bic_etl/general/scripts/bic_etl.js -p cdos/business/nonprofit -t  "Federal Tax-Exempt Subsection Codes in Colorado"

#CMD ["java","-jar","/home/joe/bic_etl/general/datasync/DataSync-1.8.2.jar","-t","LoadPreferences","-c","/home/joe/bic_etl/general/datasync/config.json";"node","/home/joe/bic_etl/general/scripts/bic_etl.js",$options]

# CMD ["java","-jar","/home/joe/bic_etl/general/datasync/DataSync-1.8.2.jar","-t","LoadPreferences","-c","/home/joe/bic_etl/general/datasync/config.json"]
# ENV OPTIONS=$options
# CMD echo $options;echo $OPTIONS ; java -jar /home/joe/bic_etl/general/datasync/DataSync-1.8.2.jar -t LoadPreferences -c /home/joe/bic_etl/general/datasync/config.json; node  /home/joe/bic_etl/general/scripts/bic_etl.js $options