
class Box():
    
    def __init__(self, item = None , empty = True):
        self.item = item
        self.empty = empty
        
    def __repr__(self):
        return f"Box(item={self.item}, empty={self.empty})"

class Empty_Space:
    def __init__(self):
        self.contain = None



class Storage():

    def __init__(self):
        self.left_top = [Empty_Space(), Empty_Space()]
        self.left_mid = [Box(),Box()]
        self.left_bot = [Box(),Box()]
        self.mid_mid = [Box(),Box()]
        self.mid_top = [Box(),Box()]
        self.midt_bot = [Box(),Box()]
        self.right_mid = [Box(),Box()]
        self.right_top = [Box(),Box()]
        self.right_bot = [Box(),Box()]
        self.storage = [self.left_top, self.midtop ,self.rightop, 
                        self.left_mid, self.mid_mid, self.right_mid,
                        self.left_bot, self.midbot, self.rightbot  ]

    def grab_empty_box(self):
        for i in self.storage:
            # if self.storage[i].contains(Empty_Space()):

        pass



        
