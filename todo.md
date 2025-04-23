
### Things to do and explore
---
### The Main Program
- Need to run for long time to test stability
- The core exception problems probably come from the I2C bus writing, both of the cores write stuff to the I2C bus. probably a fix is so that only one core writes data to the bus completly!
---
### The Algorithm

- The heart rate finding algorithm needs some tweaking, it finds false peaks easily if the backbeat is high
- The algorithm doesnt find peaks easily if the signal amplitude is low
---
### Networking

- Kubios send and receive is being investigated by jesse
- Online object needs to be integrated into the main code

---
