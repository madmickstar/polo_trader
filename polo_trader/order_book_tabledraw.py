'''
This Class is used to take in data and print it it table format. It is currently setup to accept
a list or tuple for the headings and a list of lists or a tuple of tuples for the results.
It is designed to dynamically adjust table widths based on the largest field entries.
'''
import ast


class tableDraw:
    #Initialising variables to be used within the class

    def __init__(self, **kwargs):
        '''
        
        Keyword arguments:

        inside kwargs
        
        headers                  - list of lists with header content - *
        rows                     - list of lists with data content - *
        print_header             - Print the header True or False

        '''
        try:
            headers, rows, print_header = self._get_querystring(kwargs)
        except Exception:
            raise
        
        self._tableDesc = headers
        self._tableRes = rows
        self._print_header = print_header
        self._widths = []
        self._headings = []
        self._valWidth =[]
        self._colWid = []

        
    def _get_querystring(self, kwargs):
    
        headers = ''
        rows = ''
        print_header = True
    
        if kwargs is not None:
            for key, value in kwargs.items():
                if key == 'headers':
                    headers = value
                elif key == 'rows':
                    rows = value
                elif key == 'print_header':
                    if not value:
                        print_header = value
                    elif isinstance(value, (int, long)):
                        print_header = value
                    elif str(value) == 'True':
                        print_header = value
                    else:
                        raise ValueError(key + ' value must be integer or True False!')
        return headers, rows, print_header
        
    
    def tableSize(self):
        '''
        This function is used to determine the column widths
        '''
        #Iterates through the results, compares string lengths and replaces smaller widths with larger ones.
        for columns in (self._tableDesc, self._tableRes):
            for column in columns:
                for index, item in enumerate(column):              
                    try:
                        self._colWid[index]
                    except (NameError, IndexError):
                        self._colWid.append(len(item))
                    else:
                        self._colWid[index] = (max(self._colWid[index], len(item)))

                    

    def tableData(self):
        '''
        This function draws the table and populates data.
        '''

        for R in self._tableRes:
            values = []
            colVal = '|'
            I = 0
            
            if self._print_header:
                self._print_table_header()
            
            #iterates through the values and adds them to a list with the widths set to the max +2
            for Y in R:
                #strips out beginning and tailing whitespace
                Y.strip()
                values.append('{:^{}}'.format(Y.replace('\n',' '),self._colWid[I]+2))
                I += 1
                
            for V in values:
                colVal += '{}|'.format(V)
                
            print(colVal)
        #print(self._separator)
  
  
    def _print_table_header(self):
        '''
        prints header row or rows
        '''
        for row in self._tableDesc:
            self._headings = []
            self._colHead = '|'
            self._separator = '+'
                           
            for index, item in enumerate(row):
                self._headings.append('{:^{}}'.format(item, self._colWid[index]+2))           
            
            #puts the headings list into a string with separators between values            
            for H in self._headings:
                self._colHead += '{}|'.format(H)
            
            #Creates the separator string
            for W in self._colWid:
                self._separator += '-'+'-'*W+'-+'
        
            print(self._separator)
            print(self._colHead)
        print(self._separator)