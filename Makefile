TARGET   = vm_test 

CXX      = g++
LINKER   = g++

CXXFLAGS = -Wall -g
LFLAGS   = -Wall  

SOURCES  := pte.cpp vm-provided.cpp ptab.cpp tlb.cpp \
            vm-student.cpp vm_test.cpp 
OBJECTS  := $(SOURCES:%.cpp=%.o)

$(TARGET): $(OBJECTS)
	$(LINKER) $(OBJECTS) $(LFLAGS) -o $@

$(OBJECTS): %.o : %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

.PHONY: clean
clean:
	-rm $(OBJECTS)

.PHONY: cleanall 
cleanall: clean
	-rm $(TARGET)
