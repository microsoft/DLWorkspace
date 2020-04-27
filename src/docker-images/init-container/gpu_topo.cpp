// https://raw.githubusercontent.com/lifengli137/gpu/master/gpu_topo.cpp

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
using namespace std; 


int main(int argc, char *argv[]){
	if(argc != 2) {
		cerr  << "Format: gpu_topo topologyMatrixFilePath" << endl;
		return 2;
	}
	char* topoFileName = argv[1];
	
	ifstream topoFile(topoFileName);
	if(!topoFile.is_open()){
		cerr  << "Topology file: " << topoFileName << " is not readable." << endl;
		return 2;
	}
	vector<vector<string> > topo;
	string readLine;
	int m = 0;
	int n = 0;
	int n2 = 0;
	size_t pos = 0;
	while(getline(topoFile, readLine)){
		int i = 0;
		vector<string> readVector;
		n = n2;
		n2 = 0;
		while((pos = readLine.find(" ", i)) != string::npos){
			readVector.push_back(readLine.substr(i, pos - i));
			i = pos + 1;
			n2++;
		}
		readVector.push_back(readLine.substr(i, readLine.length() - i));
		n2++;
		if(m > 0 && n != n2){
			cerr  << "Parse the line: " << readLine << " error" << endl;
			return 2;
		}
		topo.push_back(readVector);
		m++;
	}
	topoFile.close();
	
	if(m != n){
		cerr  << "Parse topology file error: " << endl;
		for(int i = 0; i < m; i++){
			for(int j = 0; j < m; j++){
				cerr  << topo[i][j];
			}
			cerr  << endl;
		}
		return 2;
	}
	
	vector<vector<int> > normTopo(m, vector<int>(n, 0));
	for(int i = 0; i < m; i++){
		for(int j = 0; j < n; j++){
			if(topo[i][j].compare("OK") == 0 || topo[i][j].compare("X") == 0){
				normTopo[i][j] = 1;
			}
		}
		
	}
	
	vector<int> mark(n, 0);
	for(int i = 0; i < n; i++){
		if(normTopo[0][i]){
			for(int j = 0; j < n; j++){
				if(normTopo[i][j]){
					mark[j]++;
				}
			}
		}
	}
	
	vector<int> order;
	for(int i = 0; i < n; i++){
		if(mark[i] >= n/2){
			order.insert(order.begin(), i);
		}else{
			order.push_back(i);
		}
	}
	
	for(int i = 0; i < n; i++){
		cout << order[i];
		if(i < n - 1) cout << ", "; 
	}
	
	return 0;
}
