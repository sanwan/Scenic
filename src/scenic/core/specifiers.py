
### Specifiers and associated objects

from scenic.core.distributions import Distribution, valueInContext
from scenic.core.utils import RuntimeParseError

## Support for lazy evaluation of specifiers

class DelayedArgument(Distribution):
	def __init__(self, deps, value):
		super().__init__(value)
		self.value = value
		self.requiredProperties = deps
		self.evaluated = False

	def copy(self):
		return DelayedArgument(self.requiredProperties, self.value)

	def evaluateIn(self, context):
		if not self.evaluated:
			assert all(hasattr(context, dep) for dep in self.requiredProperties)
			self.value = valueInContext(self.value(context), context)
			self.evaluated = True
			self.requiredProperties = set()
		return self.value

	def __getattr__(self, name):
		return DelayedArgument(self.requiredProperties,
			lambda context: getattr(self.evaluateIn(context), name))

	def __call__(self, *args):
		dargs = [toDelayedArgument(arg) for arg in args]
		return DelayedArgument(self.requiredProperties.union(*(darg.requiredProperties for darg in dargs)),
			lambda context: self.evaluateIn(context)(*(darg.evaluateIn(context) for darg in dargs)))

allowedOperators = [
	'__neg__',
	'__pos__',
	'__abs__',
	'__lt__', '__le__',
	'__eq__', '__ne__',
	'__gt__', '__ge__',
	'__add__', '__radd__',
	'__sub__', '__rsub__',
	'__mul__', '__rmul__',
	'__truediv__', '__rtruediv__',
	'__floordiv__', '__rfloordiv__',
	'__mod__', '__rmod__',
	'__divmod__', '__rdivmod__',
	'__pow__', '__rpow__',
	'__round__',
	'__len__',
	'__getitem__'
]
def makeDelayedOperatorHandler(op):
	def handler(self, *args):
		dargs = [toDelayedArgument(arg) for arg in args]
		return DelayedArgument(self.requiredProperties.union(*(darg.requiredProperties for darg in dargs)),
			lambda context: getattr(self.evaluateIn(context), op)(*(darg.evaluateIn(context) for darg in dargs))) 
	return handler
for op in allowedOperators:
	setattr(DelayedArgument, op, makeDelayedOperatorHandler(op))

def toDelayedArgument(thing):
	if isinstance(thing, DelayedArgument):
		return thing
	return DelayedArgument(set(), lambda context: thing)

def requiredProperties(thing):
	if hasattr(thing, 'requiredProperties'):
		return thing.requiredProperties
	return set()

## Specifiers themselves

class Specifier(object):
	def __init__(self, prop, value, deps=None, optionals={}):
		super().__init__()
		self.property = prop
		self.value = toDelayedArgument(value).copy()	# TODO improve?
		if deps is None:
			deps = set()
		deps |= requiredProperties(value)
		assert prop not in deps
		self.requiredProperties = deps
		self.optionals = optionals

	def applyTo(self, obj, optionals):
		val = self.value.evaluateIn(obj)
		assert not isinstance(val, DelayedArgument)
		setattr(obj, self.property, val)
		for opt in optionals:
			assert opt in self.optionals
			setattr(obj, opt, getattr(val, opt))

	def __str__(self):
		return f'<Specifier of {self.property}>'

## Support for property defaults

class PropertyDefault:
	def __init__(self, requiredProperties, attributes, value):
		self.requiredProperties = requiredProperties
		self.value = value

		def enabled(thing, default):
			if thing in attributes:
				attributes.remove(thing)
				return True
			else:
				return default
		self.isAdditive = enabled('additive', False)
		for attr in attributes:
			raise RuntimeParseError(f'unknown property attribute "{attr}"')

	@staticmethod
	def forValue(value):
		if isinstance(value, PropertyDefault):
			return value
		else:
			return PropertyDefault(set(), set(), lambda self: value)

	def resolveFor(self, prop, overriddenDefs):
		if self.isAdditive:
			allReqs = self.requiredProperties
			for other in overriddenDefs:
				allReqs |= other.requiredProperties
			def concatenator(context):
				allVals = [self.value(context)]
				for other in overriddenDefs:
					allVals.append(other.value(context))
				return tuple(allVals)
			val = DelayedArgument(allReqs, concatenator)
		else:
			val = DelayedArgument(self.requiredProperties, self.value)
		return Specifier(prop, val)

	def makeSpecifier(self):
		pass