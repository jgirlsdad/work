huber.asymetric<- function (y, k = 1.5, tol = 1e-06)
{
# y is the data

# default for k is 1.5
# trimming/Windsorizing  happens at 1.5 "standard deviations"
# tol is the convergence criterion. 
  
# is.na returns a logical vector as to whether the value is
# missing or not. ! is the logical negation

    y <- y[!is.na(y)]

    n <- length(y)


# starting values for the location and scale estimates.
# are the median and median absolute deviation
#    
        mu0 <- median( y)

        sL.old <- mad(y)
        sL<- sL.old
        sU<- sL.old

# complicated constant that adjusts scale to  equal a
#  standard deviation if data is normal.
#  pnorm(X) is prob  a standard normal is less that the value X
#  dnorm(X) =   (1/sqrt(2*pi)) * exp( -X**2/2)    the standard normal density
#  e.g. beta for k=1.5 is 0.7784652
    
    th <- 2 * pnorm(k) - 1
    beta <- th + k^2 * (1 - th) - 2 * k * dnorm(k)

    kk<- 0

# begin interative loop
    repeat {

        kk<- kk+1
        yy<- y
        
        upper<- mu0 + k*sU
        lower<- mu0 - k*sL
#  the Windsorizing process:        
# replace any value that is larger than   mu0 + k*sU
# with this upper limit
        
        yy[ y> upper] <- upper
# do an analagous operation  for lower bound            
        yy[ y< lower] <- lower

# new scale and location are basically the mean and standard deviation of the Windsorized values
        mu1 <- sum(yy)/n

# logical vector that indicates whether value is less than mu1 or greater        
            ind <- (yy< mu1)
            n1<- sum( ind) -1
            n2<- sum( !ind) -1
            temp<- yy - mu1
        
# upper and lower "standard deviations" reflecting skewness mofdification.
# note use of the beta constant to adjust the scale to be calibrated with
# the normal distribution.
        
            sL<- sqrt(sum( temp[ind]**2)/(n1*beta))
            sU<- sqrt(sum( temp[ !ind]**2)/ (n2*beta))

# test for converge, note that convergence is relative for the scales.
# roughly speaking we are expecting 5-6 digits of accuracy at convergence tol=1e-6
# convergence should be geometric and the algorithm should always converge.
        
        if ((abs(mu0 - mu1) < tol * sL.old)
            && (abs(sL.old - sL) < tol *sL.old)
            && (abs(sU.old - sU) < tol * sU.old)  )
            break
        
# update estimates        
        mu0 <- mu1
        sL.old <- sL
        sU.old<- sU
# back to top of loop        
    }
# returned object is a list with location, the scales as a vector of two values and the
# number of iterations 
    list(mu = mu1, s = c(sL, sU), niter=kk)
}
