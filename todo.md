
### Things to do and explore
---
### The Main Program

- Multithreading needs some exploration, it's a bit buggy right now but with a try expect hack it runs stable
- Measuring HR, drawing the hr flickers needs to be fixed, something to do with probably thread locks?,
- Other fix is a flag and doing the drawing in the second score when flag is up!
---
### The Algorithm

- The heart rate finding algorithm needs some tweaking, it finds false peaks easily if the backbeat is high
- The algorithm doesnt find peaks easily if the signal amplitude is low
---
### Networking

- Send hr-data topic is ready
- Kubios send and receive is being investigated by jesse
- Online object needs to be integrated into the main code

---
