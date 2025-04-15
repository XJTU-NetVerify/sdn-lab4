CXXFLAGS = -O2 -g -Wall -fmessage-length=0 -D_REENTRANT -std=c++11

SRC_DIR = src
OBJ_DIR = build

OBJ_NAMES = VeriFlow.o OpenFlowProtocolMessage.o Network.o EquivalenceClass.o ForwardingGraph.o ForwardingLink.o TrieNode.o Rule.o Trie.o EquivalenceRange.o Test.o net.o thread.o StringTokenizer.o
OBJS = $(addprefix $(OBJ_DIR)/, $(OBJ_NAMES))

# This makes all headers dependent to build any object files.
HEADERS = $(wildcard $(SRC_DIR)/*.h)
LIBS = -lpthread

TARGET = VeriFlow

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(LDFLAGS) -o $@ $^ $(LIBS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp $(HEADERS) | $(OBJ_DIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(OBJ_DIR):
	mkdir -p $@

clean:
	rm -f $(OBJ_DIR)/* \
		$(TARGET)
