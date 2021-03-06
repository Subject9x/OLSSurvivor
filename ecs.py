'''
Entity/Component system. See:
    Game Engine Architecture, Second Edition
    By Jason Gregory
    Page 885 

For a discussion of entity/component.

'''

import hashlib

class EntityManager:
    def __init__(self, ents=None, systems=None,
                 draw_systems=None, filters=None):
        self.ent_count = 0

        self.ents = ents
        if not self.ents:
            self.ents = {}

        self.filters = filters
        if not self.filters:
            self.filters = {}

        self.systems = systems
        if not self.systems:
            self.systems = [] # TODO: Put removal system here?

        self.draw_systems = draw_systems
        if not self.draw_systems:
            self.draw_systems = []

    def do_step(self):
        for system in self.systems:
            system.step(self.ents)

        # Hash the state for integrity

        state = []

        for ent in self.ents.values():
            state.append(tuple(sorted(ent.items())))
       

        frozen_state = tuple(state)


        # TODO: Is there a saner way to get the hash to bytes?
        state_hash = hashlib.md5(
                str(frozen_state).encode('utf-8')
                ).hexdigest().encode('utf-8')

        return state_hash
    
    def draw(self, offset):
        # This should have no side effects
        for system in self.draw_systems:
            system.draw(self.ents, offset)


    def add_ent(self, ent):
        # TODO: Could this live in the entity constructor?
        id = self.ent_count
        ent.id = id
        self.ents[id] = ent
        self.ent_count += 1
        print(ent)

    def filter(self, filter_id, **kwargs):
        return self.filters[filter_id].apply(self.ents, kwargs)

    def add_draw_system(self, new_draw_system, index=None):
        if index:
            self.draw_systems.insert(index, new_draw_system)
        else:
            self.draw_systems.append(new_draw_system)

    def add_system(self, new_system, index=None):
        if index:
            self.systems.insert(index, new_system)
        else:
            self.systems.append(new_system)
    
    def add_filter(self, new_filter, name=None):
        if name:
            self.filters[name] = new_filter
        else:
            self.filters[type(new_filter).__name__] = new_filter

    def __getitem__(self, id):
        ''' If you do ecs[id] you get the end. Convenience. ''' 
        return self.ents[id]

    def get_system(self, classname):
        ''' Gets a system, if available, by class name.
        This lets you, for example, put additional data in a
        system during a handshake. Should probably not be used
        during game because it's not fast. If fast becomes a
        need, we should make a map of systems by classname.
        '''
        for system in self.systems:
            if type(system).__name__ == classname:
                return system


class Filter:
    ''' Abstract class for a filter object which has an 'apply' method
    which accepts a dict of criteria and returns a list of ids of ents that
    match that criterium. '''

    def apply_individual(self, ent, criteria):
        pass

    def apply(self, ents, criteria):
        ''' Checks each ent and returns the id if it meets the criteria
        (if we return something from check_individual)
        This can be overridden if the Filter, for example, cares about the
        whole state rather than each ent's state.'''
        return [result.id for result in 
                [self.apply_individual(ent, criteria)
                    for id, ent in ents.items()]
                if result]


class System:
    ''' Abstract base class for system
    To use, override the "criteria" array of components to look for (in
    your constructor) and override the do_step function to.'''
    def __init__(self):
        self.criteria = []

    def step(self, ents):
        ''' This is called with a list of every ent, regardless of
        what components they contain. If the system needs this (or
        always affects all ents) override this. '''
        self.do_step_all([ent for ent in ents.values()
                if all([comp in ent for comp in self.criteria])])

    def do_step_all(self, ents):
        ''' This is called with a list of ents that matches the
        criteria. Override it for systems where ents affect each
        other, like gravity or magnetism '''
        for ent in ents:
            self.do_step_individual(ent)

    def do_step_individual(self, ent):
        '''By default this is called for every ent that meets the
        criteria. Use this for systems where every ent moves
        independantly, such as velocity.'''
        pass

class DrawSystem:
    ''' Abstract base class for draw systems '''
    def __init__(self):
        self.criteria = []

    def draw(self, unfiltered_list, offset):
        ''' This is called with a list of all of the ents. If the system
        needs filtering beyond checking criteria, override this method.'''
        self.draw_all([ent for ent in unfiltered_list.values()
                if all([comp in ent for comp in self.criteria])], offset)

    def draw_all(self, ents, offset):
        ''' This is called on all ents that meet criteria. Use this to
        do draws that involve multiple entities '''
        for ent in ents:
            self.draw_individual(ent, offset)

    def draw_individual(self, ent, offset):
        '''Called for each ent that meets the criteria. Use this for
        simple drawing, such as drawing a sprite for each unit.'''
        pass


class Entity(dict):

    ''' Credit due to this stack overflow question:
    http://stackoverflow.com/a/23689767/1048464
    Essentially an entity is just a dict. What this class
    gives us is a type and .notation access to members
    (so you can write code that uses entities in a pythonic
    way and not care about what members it does or does not
    have.

    Note that beecause this is a dict, you can just pass
    a dict of the components you'd like in and it'll just
    work.
    
    Ensure that all components implement .to_string because
    that is how sync is ensured.

    '''



    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    

class DeletionSystem(System):
    def __init__(self, mgr):
        self.mgr = mgr
        self.criteria = ['delete', 'id']

    def do_step_all(self, ents):
        to_delete = []

        for ent in ents:
            to_delete.append(ent.id)

        for id in to_delete:
           del self.mgr.ents[id]

