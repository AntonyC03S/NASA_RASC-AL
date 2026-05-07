
class Box():
    
    def __init__(self, item = None):
        self.item = item
        if item is not None: 
            self.empty = False
        else:
            self.empty = True
        
    def __repr__(self):
        return f"Box(item={self.item})"

class Empty_Space:
    def __init__(self):
        self.contain = None

    def __repr__(self):
        return f"Empty_space"



class Storage():

    def __init__(self):
        self.left_top = [Empty_Space(), Empty_Space()]
        self.left_mid = [Box("Dust"),Box("Dust")]
        self.left_bot = [Box("Rocks"),Box("Rocks")]
        self.mid_mid = [Box(),Box()]
        self.mid_top = [Box(),Box()]
        self.mid_bot = [Box(),Box()]
        self.right_mid = [Box(),Box()]
        self.right_top = [Box(),Box()]
        self.right_bot = [Box(),Box()]
        self.storage = [self.left_top, self.mid_top ,self.right_top, 
                        self.left_mid, self.mid_mid, self.right_mid,
                        self.left_bot, self.mid_bot, self.right_bot  ]

    def find_empty_position(self):
        for location, section in enumerate(self.storage):
            if any(isinstance(x, Empty_Space) for x in section):
                return location + 1 , section
        return 0 , 0
    
    def place_box(self, section, box):
        if isinstance(section[1], Empty_Space):
            section[1] = box
        elif isinstance(section[0], Empty_Space):
            section[0] = box
        else:
            return False
        return True
    
    def take_empty(self):
        for location, section in enumerate(self.storage):
            if isinstance(section[0], Box):
                if section[0].empty:
                    box = section[0]
                    section[0] = Empty_Space()
                    break
            elif isinstance(section[1], Box):
                if section[1].empty:
                    box = section[1]
                    section[1] = Empty_Space()
                    break
        else:
            return False
        
        return box



    def display_storage(self):
        print(f"""{self.storage[0][0]}    {self.storage[1][0]}   {self.storage[2][0]}
{self.storage[0][1]}    {self.storage[1][1]}   {self.storage[2][1]} \n\n
{self.storage[3][0]}    {self.storage[4][0]}   {self.storage[5][0]} 
{self.storage[3][1]}    {self.storage[4][1]}   {self.storage[5][1]} \n\n
{self.storage[6][0]}    {self.storage[7][0]}   {self.storage[8][0]} 
{self.storage[6][1]}    {self.storage[7][1]}   {self.storage[8][1]} \n"""    )


if __name__ == "__main__":
    s = Storage()
    
    while True:
        command = input("Command: Place or Get\n")
        if command == "Place":
            print(f"Placing")
            _ , empty_postion = s.find_empty_position()
            if empty_postion == 0:
                print("Storage Full")
                continue
            else:
                s.place_box(empty_postion, Box("Rock"))
        elif command == "Get":
            print(f"Getting")
            if not s.take_empty():
                print("Out of enmpty boxes")
                continue
        else:
            print("Command not found")
        s.display_storage()