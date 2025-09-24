#FROM centos:7
#FROM centos/nodejs-10-centos7
# install git 
# RUN yum install -y git

#RUN yum install java
#RUN yum install -y gcc-c++ make 
#RUN 

FROM centos/python-36-centos7:1
#RUN curl -O https://download.java.net/java/GA/jdk18.0.1.1/65ae32619e2f40f3a9af3af1851d6e19/2/GPL/openjdk-18.0.1.1_linux-x64_bin.tar.gz 

#RUN tar xvf openjdk-18.0.1.1_linux-x64_bin.tar.gz 
CMD ["node","/home/joe/bic_etl/general/scripts/bic_etl.js","-p","cdos/business/nonprofit","-t","Federal Tax-Exempt Subsection Codes in Colorado"]