import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils

def compareDependencyEdgesById(dep1, dep2):
    id1 = dep1[2].get("id")
    id2 = dep2[2].get("id")
    if id1 > id2:
       return 1
    elif id1 == id2:
       return 0
    else: # x<y
       return -1


class GeneralEntityTypeRecognizer(ExampleBuilder):
    def __init__(self, style=None):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        self.styles = style
        assert( self.classSet.getId("neg") == 1 )

    def preProcessExamples(self, allExamples):
        if "normalize" in self.styles:
            print >> sys.stderr, " Normalizing feature vectors"
            ExampleUtils.normalizeFeatureVectors(allExamples)
        return allExamples   
    
    def getMergedEntityType(self, entities):
        types = set()
        for entity in entities:
            types.add(entity.get("type"))
        types = list(types)
        types.sort()
        typeString = ""
        for type in types:
            if typeString != "":
                typeString += "---"
            typeString += type
        return typeString

    def buildLinearOrderFeatures(self,sentenceGraph,index,tag,features):
        t = sentenceGraph.tokens[index]
        features[self.featureSet.getId("linear_"+tag+"_txt_"+sentenceGraph.getTokenText(t))] = 1
        features[self.featureSet.getId("linear_"+tag+"_POS_"+t.get("POS"))] = 1
        if sentenceGraph.tokenIsName[t]:
            features[self.featureSet.getId("linear_"+tag+"_isName")] = 1
            for entity in sentenceGraph.tokenIsEntityHead[t]:
                if entity.get("isName") == "True":
                    features[self.featureSet.getId("linear_"+tag+"_annType_"+entity.get("type"))] = 1
    
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        namedEntityCount = 0
        for entity in sentenceGraph.entities:
            if entity.get("isName") == "True": # known data which can be used for features
                namedEntityCount += 1
        namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
        
        bagOfWords = {}
        for token in sentenceGraph.tokens:
            text = "bow_" + token.get("text")
            if not bagOfWords.has_key(text):
                bagOfWords[text] = 0
            bagOfWords[text] += 1
            if sentenceGraph.tokenIsName[token]:
                text = "ne_" + text
                if not bagOfWords.has_key(text):
                    bagOfWords[text] = 0
                bagOfWords[text] += 1
        
        self.inEdgesByToken = {}
        self.outEdgesByToken = {}
        for token in sentenceGraph.tokens:
            inEdges = sentenceGraph.dependencyGraph.in_edges(token)
            inEdges.sort(compareDependencyEdgesById)
            self.inEdgesByToken[token] = inEdges
            outEdges = sentenceGraph.dependencyGraph.out_edges(token)
            outEdges.sort(compareDependencyEdgesById)
            self.outEdgesByToken[token] = outEdges
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token]:
                continue
            
            # CLASS
            if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
                category = self.classSet.getId(self.getMergedEntityType(sentenceGraph.tokenIsEntityHead[token]))
            else:
                category = 1
            
            # FEATURES
            features = {}
            
            features[self.featureSet.getId(namedEntityCountFeature)] = 1
            for k,v in bagOfWords.iteritems():
                features[self.featureSet.getId(k)] = v
            
#            for j in range(len(sentenceGraph.tokens)):
#                text = "bow_" + sentenceGraph.tokens[j].get("text")
#                if j < i:
#                    features[self.featureSet.getId("bf_" + text)] = 1
#                elif j > i:
#                    features[self.featureSet.getId("af_" + text)] = 1
        
            # Main features
            text = token.attrib["text"]
            features[self.featureSet.getId("txt_"+text)] = 1
            features[self.featureSet.getId("POS_"+token.attrib["POS"])] = 1
            stem = PorterStemmer.stem(text)
            features[self.featureSet.getId("stem_"+stem)] = 1
            features[self.featureSet.getId("nonstem_"+text[len(stem):])] = 1
            
            # Linear order features
            for index in [-3,-2,-1,1,2,3]:
                if i + index > 0 and i + index < len(sentenceGraph.tokens):
                    self.buildLinearOrderFeatures(sentenceGraph, i + index, str(index), features)
            
            # Content
            if i > 0 and text[0].isalpha() and text[0].isupper():
                features[self.featureSet.getId("upper_case_start")] = 1
            for j in range(len(text)):
                if j > 0 and text[j].isalpha() and text[j].isupper():
                    features[self.featureSet.getId("upper_case_middle")] = 1
                # numbers and special characters
                if text[j].isdigit():
                    features[self.featureSet.getId("has_digits")] = 1
                    if j > 0 and text[j-1] == "-":
                        features[self.featureSet.getId("has_hyphenated_digit")] = 1
                elif text[j] == "-":
                    features[self.featureSet.getId("has_hyphen")] = 1
                elif text[j] == "/":
                    features[self.featureSet.getId("has_fslash")] = 1
                elif text[j] == "\\":
                    features[self.featureSet.getId("has_bslash")] = 1
                # duplets
                if j > 0:
                    features[self.featureSet.getId("dt_"+text[j-1:j+1].lower())] = 1
                # triplets
                if j > 1:
                    features[self.featureSet.getId("tt_"+text[j-2:j+1].lower())] = 1
            
            # Attached edges
            t1InEdges = sentenceGraph.dependencyGraph.in_edges(token)
            t1InEdges.sort(compareDependencyEdgesById)
            for edge in t1InEdges:
                edgeType = edge[2].attrib["type"]
                features[self.featureSet.getId("t1HangingIn_"+edgeType)] = 1
                features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["POS"])] = 1
                features[self.featureSet.getId("t1HangingIn_"+edgeType+"_"+edge[0].attrib["POS"])] = 1
                tokenText = sentenceGraph.getTokenText(edge[0])
                features[self.featureSet.getId("t1HangingIn_"+tokenText)] = 1
                features[self.featureSet.getId("t1HangingIn_"+edgeType+"_"+tokenText)] = 1
            t1OutEdges = sentenceGraph.dependencyGraph.out_edges(token)
            t1OutEdges.sort(compareDependencyEdgesById)
            for edge in t1OutEdges:
                edgeType = edge[2].attrib["type"]
                features[self.featureSet.getId("t1HangingOut_"+edgeType)] = 1
                features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["POS"])] = 1
                features[self.featureSet.getId("t1HangingOut_"+edgeType+"_"+edge[1].attrib["POS"])] = 1
                tokenText = sentenceGraph.getTokenText(edge[1])
                features[self.featureSet.getId("t1HangingOut_"+tokenText)] = 1
                features[self.featureSet.getId("t1HangingOut_"+edgeType+"_"+tokenText)] = 1
             
            extra = {"xtype":"token","t":token}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
            
            # chains
            self.buildChains(token, sentenceGraph, features)
        return examples
    
    def buildChains(self,token,sentenceGraph,features,depthLeft=3,chain="",visited=None):
        if depthLeft == 0:
            return
        
        if visited == None:
            visited = []

        inEdges = self.inEdgesByToken[token]
        outEdges = self.outEdgesByToken[token]
        for edge in inEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                nextToken = edge[0]
                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
                    if entity.get("isName") == "True":
                        features[self.featureSet.getId("name_dist_"+str(depthLeft))] = 1
                        features[self.featureSet.getId("name_dist_"+str(depthLeft)+entity.get("type"))] = 1
                features[self.featureSet.getId("dep_dist_"+str(depthLeft)+edgeType)] = 1
                features[self.featureSet.getId("POS_dist_"+str(depthLeft)+nextToken.get("POS"))] = 1
                tokenText = sentenceGraph.getTokenText(nextToken)
                features[self.featureSet.getId("text_dist_"+str(depthLeft)+tokenText)] = 1
                features[self.featureSet.getId("chain_dist_"+str(depthLeft)+chain+"-frw_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-frw_"+edgeType,visited+inEdges+outEdges)

        for edge in outEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                nextToken = edge[1]
                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
                    if entity.get("isName") == "True":
                        features[self.featureSet.getId("name_dist_"+str(depthLeft))] = 1
                        features[self.featureSet.getId("name_dist_"+str(depthLeft)+entity.get("type"))] = 1
                features[self.featureSet.getId("dep_dist_"+str(depthLeft)+edgeType)] = 1
                features[self.featureSet.getId("POS_dist_"+str(depthLeft)+nextToken.get("POS"))] = 1
                tokenText = sentenceGraph.getTokenText(nextToken)
                features[self.featureSet.getId("text_dist_"+str(depthLeft)+tokenText)] = 1
                features[self.featureSet.getId("chain_dist_"+str(depthLeft)+chain+"-rev_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-rev_"+edgeType,visited+inEdges+outEdges)
