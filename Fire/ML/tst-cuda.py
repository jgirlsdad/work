import numpy as np
import os
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential,load_model
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
#from keras.optimizers import Adam
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.optimizers.schedules import ExponentialDecay
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.callbacks import LearningRateScheduler
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  
tf.get_logger().setLevel('ERROR')  # Only show ERROR messages
import pymongo,json
import datetime,sys
import sqlite3
from tensorflow.keras import mixed_precision
mixed_precision.set_global_policy("mixed_float16")  # use Tensor Cores on RTX 3080

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        tf.config.set_visible_devices(gpus[0], 'GPU')  # optional: pick the first GPU
        tf.config.experimental.set_memory_growth(gpus[0], True)
        print("Using GPU:", gpus[0])
    except Exception as e:
        print("GPU config warning:", e)

def getClimateIndices(directory):
    temp = []  # temporary list/dict used throught the program 
 #   features = pd.DataFrame()  # this is a Pandas Dataframe that will hold the Climate Indices
    features={}
    #  add year-month pairs to the features dataframe that will match the available data
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_file():
             #   print(entry.name)
    #  the Climate Indices are stored in flat files, so read them all in and store them in features
                file=entry.name
                file = file.rstrip("\n")
                spl = file.split(".")
                name = spl[0]
                temp = []
                tempdf = pd.DataFrame()
                print(file)
                if file.find("Zone.Identifier") == -1:
                    spl=file.split(".")
                    name=".".join(spl[:-1])
                    with open(f"{directory}/{file}","r") as fin:
                        line=fin.readline()
                        spl = line.split()
                        start = int(spl[0])
                        end = int(spl[1])
                        nl=0
                        print(start,end)
                        process=True
                        for nn in range(start,end+1):
                           line = fin.readline()
                           spl = line.split()
                           year = int(spl[0])
                           if year > 1949  and year < 2024:
                               for mon in range(1,13):
                                   val=float(spl[mon])
                                   if val < -30:
                                       process=False
                                       print(file,year,mon,val)
                        fin.close()
                    if process: 
                        with open(f"{directory}/{file}","r") as fin:
                            line=fin.readline()
                            spl = line.split()
                            start = int(spl[0])
                            end = int(spl[1])
                            nl=0
                            print(start,end)
                            process=True
                            for nn in range(start,end+1):
                               line = fin.readline()
                               spl = line.split()
                               year = int(spl[0])
                               if year not in features:
                                   features[year]={}
                                   
                               for mon in range(1,13):
                                   if mon not in features[year]:
                                       features[year][mon]={}
                                   val=float(spl[mon])
                                   features[year][mon][name]=val
                    else:
                        print("SKIPPING ",file)
                            
        return features

def getIndices(climate,start,end,indices=["all"]):
    features=[]
    features4Pbi=[]
    noUse={}
    indicesToUse={}

    frufru=[]
    for year,dct in climate.items():
        if year > 1989 and year < 2025:
            for mo,dct2 in dct.items():
                for ds,val in dct2.items():
                    if val < -30:
                        if ds not in noUse:
                            noUse[ds]=0
                        noUse[ds]+=1

    
    for year in range(start,end+1):
        dct=climate[year]

        for month,dct2 in dct.items():
            tmp=[]
            tmp2=[]
            tmp.append(year)
            tmp.append(month)
            tmp.append(f"{year}{str(month).zfill(2)}01")
            for name,val in sorted(dct2.items()):
                if (indices[0]=="all" or name in indices) and name not in noUse:
                  tmp.append(val)
                  tmp2.append(val)
                
                  if name not in indicesToUse:
                      indicesToUse[name]=0
                  indicesToUse[name]+=1
            features4Pbi.append(tmp)
            features.append(tmp2)
    return features,indicesToUse,features4Pbi 

climate=getClimateIndices("data/Climate-Indices")
features,indicesToUse,features4Pbi=getIndices(climate,1990,2024,["all"])


def readWxData(db):
    connr = sqlite3.connect('/home/joe/Fire/Data/DB/era5DataMeans.db',)
    df=pd.read_sql('select * from MEANS_TTdRHVPD', connr)
    return df

def selectWxData(df,point,var="T"):    
    data=df.loc[df["Point"] == point]
    yrmos=df.loc[df["Point"] == point,"Yrmo"].astype(int).values
    mos=df.loc[df["Point"] == point,"Yrmo"].str[4:6].astype(int).values
    
    data=data[[var]].values.tolist()
    
    return data,yrmos,mos

df=readWxData('/home/joe/Fire/Data/DB/era5DataMeans.db')
wxData,yrmos,mos=selectWxData(df,10,"VPD") 

def toMongo(collection,what): 
    db = client.Fire
    
    # use a collection named "recipes"
    my_collection = db[collection]
    
    try: 
     result = my_collection.insert_many(what)
    
    # return a friendly error if the operation fails
    except pymongo.errors.OperationFailure:
      print("An authentication error was received. Are you sure your database user is authorized to perform write operations?")
      sys.exit(1)
    else:
      inserted_count = len(result.inserted_ids)
      print("I inserted %x documents." %(inserted_count))
    
      print("\n")

def mongoConnect():    
    try:
      client = pymongo.MongoClient("mongodb+srv://jcomeaux:444Jayla.@cluster0.qjm0b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
      
    # return a friendly error if a URI error is thrown 
    except pymongo.errors.ConfigurationError:
      print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
      sys.exit(1)
        
    return client

    

# Define model parameters
timesteps = 24  # Number of timesteps
nfeatures = len(features[0])    # Number of features (multivariate)
batch_size = 48  # Batch size
nforecast=8
# Generate data
#X, y = generate_multivariate_data(timesteps, features, 1000)

#climate=getClimateIndices("ML/data/Climate-Indices")
#features,indicesToUse,features4Pbi=getIndices(climate,1990,2024,["all"])


df=readWxData('/home/joe/work/Fire/Data/DB/era5DataMeans.db')
wxData,yrmos,mos=selectWxData(df,500,"VPD") 

def predicting(features,wxData,yrmos,mos,weights,date):
    timesteps = 24  # Number of timesteps
    nfeatures = len(features[0])    # Number of features (multivariate)
    batch_size = 48  # Batch size
    neurons= 300
    epochs = 300
    nforecast=8
    stateful=True
    changeWeights=False
    writeResults=False
    shuffle=False
    results = {"statefule":stateful,
               "batch_size":batch_size,
               "forecast_period":nforecast,
               "neurons":neurons,
               "features":nfeatures,
               "timesteps":timesteps,
               "shuffle":shuffle,
               "TotalLength":len(features),
               "modelBestCorrected":True}
    featuresShift = features[nforecast:]
    wxDataShift=wxData[:-nforecast]
    yrmoShift=yrmos[:-nforecast]
    mosShift=mos[:-nforecast]
    
   
    nlen=len(featuresShift)
    X=[]
    for nn in range(timesteps,nlen):
        tmp=featuresShift[nn-timesteps:nn]
        X.append(tmp)
    
    X=np.array(X)
    #wxData_scaled = scaler.fit_transform(wxData)
    y=np.array(wxDataShift[timesteps:])
    
    
    print(X.shape)
    print(y.shape)
    
    scaler = MinMaxScaler()
    Xscaled = scaler.fit_transform(X.reshape(-1,1))
    yScaled=scaler.fit_transform(y)
    Xscaled = Xscaled.reshape(X.shape)
 
    # Reshape data to match batch size
    # X = X[:(X.shape[0]//batch_size)*batch_size,:,:]
    # y = y[:(y.shape[0]//batch_size)*batch_size,:]
    
    
    nlen= len(Xscaled)
    nn = int(nlen*.8)
    X_train = Xscaled[:nn]
    X_test = Xscaled[nn:]
    y_train = yScaled[:nn]
    y_test = yScaled[nn:]

    yrmo_train=yrmoShift[:nn]
    yrmo_test=yrmoShift[nn:]
    mos_train=mosShift[:nn]
    mos_test=mosShift[nn:]
    
    X_train = X_train[:(X_train.shape[0]//batch_size)*batch_size,:,:]
    y_train = y_train[:(y_train.shape[0]//batch_size)*batch_size,:]
    
    X_test = X_test[:(X_test.shape[0]//batch_size)*batch_size,:,:]
    y_test = y_test[:(y_test.shape[0]//batch_size)*batch_size,:]

    histories=[]
    

    initial_learning_rate = 0.002
    lr_schedule = ExponentialDecay(
        initial_learning_rate,
        decay_steps=10000,
        decay_rate=0.56,
        staircase=True
    )
    lr_schedule_callback = ReduceLROnPlateau(
          monitor='loss', factor=0.2, patience=10, min_lr=0.00001, verbose=1
    )
    class LearningRateLogger(tf.keras.callbacks.Callback):
        def on_epoch_begin(self, epoch, logs=None):
            lr = self.model.optimizer._decayed_lr(tf.float32).numpy()
            print(f'Epoch {epoch+1}: Learning rate is {lr:.6f}')

    
    def lr_schedule(epoch, initial_lr):
        return initial_lr * np.exp(-0.1 * epoch)

    lr_scheduler = LearningRateScheduler(lr_schedule)

# Compile the model with Adam optimizer and mean squared error loss
#    optimizer = Adam(learning_rate=initial_learning_rate)
    optimizer = Adam(learning_rate=initial_learning_rate)
    
    results["learningRate"]=initial_learning_rate
  
    
 #   optimizer = Adam(learning_rate=.002)
    # Define the model
    if stateful == False:
        model = Sequential()
        model.add(LSTM(neurons, stateful=stateful, input_shape=(batch_size, timesteps, nfeatures)))
        model.add(Dense(1))  # Output layer with 1 feature
        model.compile(loss='mse', optimizer=optimizer)
        if weights is not None and changeWeights == True:
            model.set_weights(weights)
      #      print("setting weights",weights)
        history=model.fit(X_train, y_train, epochs=epochs, verbose=0,batch_size=batch_size, 
                          shuffle=shuffle, callbacks=[lr_schedule_callback])
        for key,lst in history.history.items():
            history.history[key] = [float(val) for val in history.history[key]]
        results['history']= history.history
        modelBest=model
        epochs_check=epochs
        epochBest=epochs
        yhat = modelBest.predict(X_test, batch_size=batch_size)
        y_train_hat = modelBest.predict(X_train, batch_size=batch_size)
        
    elif stateful: 
    # Train the model
        print("Stateful ")
        model = tf.keras.Sequential([
         tf.keras.Input(batch_shape=(batch_size, timesteps, nfeatures)),  # fixed batch size here
         tf.keras.layers.LSTM(150, stateful=True),                        # no batch_input_shape arg
         tf.keras.layers.Dense(1)
       ])
        model.compile(loss='mse', optimizer=optimizer)

        # model = Sequential()
        # model.add(LSTM(150, stateful=stateful, batch_input_shape=(batch_size, timesteps, nfeatures)))
        # model.add(Dense(1))  # Output layer with 1 feature
        # model.compile(loss='mse', optimizer=optimizer)
#        history=model.fit(X_train, y_train, epochs=epochs, verbose=0,batch_size=batch_size, shuffle=True,callbacks=[lr_schedule_callback])
        history=model.fit(X_train, y_train, epochs=epochs, verbose=0,batch_size=batch_size, shuffle=shuffle)
        if weights is not None and changeWeights == True:
            model.set_weights(weights)
      #      print("setting weights",weights)
        
        # Train the model
        percent=.10
        epochs_check=int(epochs*percent)
        lossBest=np.inf
        newWeights=None
        best_model_path = 'best_model.h5'
        losses=[]
        learns=[]
        for i in range(epochs):
            if newWeights is not None and changeWeights == True:
                model.set_weights(newWeights)
#            history=model.fit(X_train, y_train, epochs=1, verbose=0,batch_size=batch_size, shuffle=True,callbacks=[lr_schedule_callback])
                history=model.fit(X_train, y_train, epochs=1, verbose=0,batch_size=batch_size, shuffle=shuffle)
            for layer in model.layers:
                if hasattr(layer, "reset_states"):
                    layer.reset_states()
#            model.reset_states()
            loss = history.history["loss"][0]
      #      histories.append({"loss":float(loss),"LR":float(history.history["lr"][0])}) 
            losses.append(float(loss))
            if "lr" in history.history:
                learns.append(float(history.history["lr"][0]))
            if loss < lossBest:
                lossBest=loss
 #               model.save(best_model_path)
                best_model_path = "best_model.keras"   # instead of .h5
                model.save(best_model_path)      
                newWeights=model.get_weights()
                print(f"Epoch {i + 1}: Loss improved to {loss}. Saving model.")
                historyBest=history
                epochBest=i
            if i-epochBest > epochs_check:
                print("Short Stop ",i)
                break   
        # Load the best model
        modelBest = load_model(best_model_path)
        modelBest=model
        results['history'] = {"loss":losses,"lr":learns}
        epochBest=epochs
    # Make predictions
        yhat = modelBest.predict(X_test, batch_size=batch_size)
        y_train_hat = modelBest.predict(X_train, batch_size=batch_size)
        
    yhat= scaler.inverse_transform(yhat)
    y_train_hat= scaler.inverse_transform(y_train_hat)
    
    y_train = scaler.inverse_transform(y_train)
    y_test = scaler.inverse_transform(y_test)
    
    results["learningRate"]=initial_learning_rate
    results["earlyStoppingLength"]=epochs_check
    results["epochBest"]=epochBest
    results["changeWeights"]=changeWeights
    results["date"]=date
    results["testError"] = sum([float(abs(y_test[nn]-yhat[nn])) for nn in range(len(y_test))])/len(y_test) 
    results["trainError"] = sum([float(abs(y_train[nn]-y_train_hat[nn])) for nn in range(len(y_train))])/len(y_train) 
    results["y_test"]=[float(yy) for yy in y_test]
    
    results["y_hat"]=[float(yy) for yy in yhat]
    modelBest = tf.keras.models.load_model(best_model_path, compile=False)
    modelBest.compile(optimizer=optimizer,loss=tf.keras.losses.MeanSquaredError())
    
 #   results["histories"]=histories
    if writeResults:
        try:
            toMongo("VPD",[results])
        except Exception as err:
            print("Error: ",err)
    
    return modelBest,y_test,yhat,yrmo_test,mos_test,history

diffs={}
models={}
data={}
weights=None
client = mongoConnect()
now1=datetime.datetime.today()
for nn in range(10):
    model,y_test,yhat,yrmo_test,mos_test,hist=predicting(features,wxData,yrmos,mos,weights,now1)
    ydiff = [abs(y_test[nn]-yhat[nn]) for nn in range(len(y_test))]
    print(sum(ydiff)/len(ydiff))
    weights=model.get_weights()
    models[nn]=model
    data[nn]=[]
    data[nn].append(y_test)
    data[nn].append(yhat)
    diffs[nn]=sum(ydiff)/len(ydiff)

now2=datetime.datetime.today()

print("DONE ",now2-now1)