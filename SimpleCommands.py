import discord
import asyncio
from datetime import datetime
import gspread 
from oauth2client.service_account import ServiceAccountCredentials

import SecretStuff
import MoBotDatabase

moBot = 449247895858970624
moBotTest = 476974462022189056
mo = 405944496665133058

spaceChar = "⠀"
OK_EMOJI = "🆗"
ONE_EMOJI = "1⃣"
TWO_EMOJI = "2⃣"
FLOPPY_DISK_EMOJI = "💾"
MAG_EMOJI = "🔍"
CHECKMARK_EMOJI = "✅"
X_EMOJI = "❌"
NUMBER_SIGN_EMOJI = "#⃣"

class Command:
  def __init__(self, command_id, trigger, response, referencingMessage):
    self.command_id = command_id
    self.trigger = trigger.decode('utf-8')
    self.response = response.decode('utf-8')
    self.referencingMessage = "Yes" if referencingMessage == 1 else "No"
# end Command

async def main(args, message, client):
  now = datetime.now()
  for i in range(len(args)):
    args[i].strip()

  if (args[1] in ["new", "add", "create"]):
    await createCommandSession(message, client)
  elif (args[1] in ["change", "edit", "alter"]):
    await editCommandSession(args, message, client)
  elif (args[1] in ["remove", "delete"]):
    await deleteCommand(args, message, client)
  elif (args[1] == "commands"):
    await displayCommands(message, client)
# end main

async def mainReactionAdd(message, payload, client): 
  embed = message.embeds[0]
  commandOwner = message.guild.get_member(int(embed.author.url.split("command_owner_id=")[1].split("/")[0]))

  authorPerms = message.channel.permissions_for(message.author)
  if (not authorPerms.manage_messages):
    await message.channel.send("**Not Permitted**\nOnly members with the Manage Message permission may create/edit/delete MoBot Custom Commands.")
    return

  if (payload.user_id == commandOwner.id):
    if (payload.emoji.name == ONE_EMOJI):
      await handleNewTrigger(commandOwner, message, embed)
    elif (payload.emoji.name == TWO_EMOJI):
      await handleNewResponse(commandOwner, message, embed)
    elif (payload.emoji.name == FLOPPY_DISK_EMOJI):
      await saveCommand(message, embed)
    elif (payload.emoji.name == MAG_EMOJI):
      await displayFullResponse(message, embed)
  if (payload.emoji.name not in [NUMBER_SIGN_EMOJI]):
    await message.remove_reaction(payload.emoji.name, message.guild.get_member(payload.user_id))
# end mainReactionAdd

async def mainReactionRemove(message, payload, client):
  pass
# end mainReactionRemove

async def memberJoin(member):
  pass
# end memberJoin

async def memberRemove(member, client):
  pass
# end memberRemove

async def sendCommand(message, command):
  response = command[2].decode('utf-8')
  referencing_message = command[7]
  await message.channel.trigger_typing()

  if (referencing_message == 1):
    msg = None
    for channel in message.guild.text_channels:
      try:
        msg = await channel.fetch_message(int(response))
        break
      except discord.errors.NotFound:
        pass

    if (msg is None):
      pass
    else:
      if (msg.embeds and msg.content is not ""): # msg.embeds not blank and content not blank
        await message.channel.send(embed=msg.embeds[0], content=msg.content)
      elif (msg.embeds):
        await message.channel.send(embed=msg.embeds[0])
      elif (msg.content is not ""):
        await message.channel.send(content=msg.content)
  else:
    await message.channel.send(response)
# end sendCommand

async def displayFullResponse(message, embed):
  await message.channel.send("``` %s ```" % embed.fields[1].value)
# end displayFullResponse

async def displayCommands(message, client):
  embed = discord.Embed(color=int("0xd1d1d1", 16))
  embed.set_author(name="MoBot Custom Commands", icon_url=client.user.avatar_url, url="https://google.com/SimpleCommands/")
  commandList = getGuildCommands(message.guild.id)
  commandsString = "\n__Trigger -- Response__\n"
  for command in commandList:
    commandsString += "%s. %s -- %s%s\n" % (commandList.index(command) + 1, command.trigger, command.response[:20], ("..." if len(command.response) >= 20 else ""))
  embed.description = "---\n**%s Commands**\n%s\n---" % (message.guild.name, commandsString[:-1])
  await message.channel.send(embed=embed)
# end displayCommands

async def deleteCommand(args, message, client):
  mc = " ".join(args)
  trigger = mc.split("%s %s" % (args[1], args[2]))[1].strip() # split on "delete command"
  command = triggerExists(trigger, getGuildCommands(message.guild.id))

  if (command is None):
    embed = discord.Embed(color=int("0xd1d1d1", 16))
    embed.set_author(name="MoBot Custom Commands", icon_url= client.user.avatar_url)
    embed.description = "---\n**COMMAND NOT FOUND**\nA command with the trigger `%s` was not found. To view this server's commands, use `@MoBot#0697 commands`.\n---" % trigger
    await message.channel.send(embed=embed)
    return
  else:
    def checkEmoji(payload):
      return payload.user_id == message.author.id and payload.channel_id == message.channel.id and payload.emoji.name in [CHECKMARK_EMOJI, X_EMOJI]
    # end checkEmoji

    msg = await message.channel.send("**Delete this command?**")
    await msg.add_reaction(CHECKMARK_EMOJI)
    await msg.add_reaction(X_EMOJI)
    try:
      payload = await client.wait_for("raw_reaction_add", timeout=60, check=checkEmoji)
    except asyncio.TimeoutError:
      await msg.clear_reactions()
      await msg.edit(content="~~ %s ~~\n**TIMED OUT**" % (msg.content))
      return
    
    if (payload.emoji.name == CHECKMARK_EMOJI):
      moBotDB = MoBotDatabase.connectDatabase()
      moBotDB.connection.commit()
      moBotDB.cursor.execute("""
      DELETE FROM 
        custom_commands
      WHERE 
        custom_commands.command_id = '%s'""" % command.command_id)
      moBotDB.connection.commit()
      moBotDB.connection.close()

      await msg.clear_reactions()
      await msg.edit(content="~~ %s ~~\n**DELETED**" % (msg.content))

    elif (payload.emoji.name == X_EMOJI):
      await msg.clear_reactions()
      await msg.edit(content="~~ %s ~~\n**CANCELED**" % (msg.content))
# end deleteCommand

async def editCommandSession(args, message, client): # for editing commands
  embed = discord.Embed(color=int("0xd1d1d1", 16))
  embed.set_author(name="MoBot Custom Commands", icon_url=client.user.avatar_url, url="https://google.com/SimpleCommands/command_id=None/guild_id=%s/command_owner_id=%s" % (message.guild.id, message.author.id))

  mc = " ".join(args)
  trigger = mc.split("%s %s" % (args[1], args[2]))[1].strip() # split on "edit command"
  command = triggerExists(trigger, getGuildCommands(message.guild.id))

  if (command is None):
    embed.description = "---\n**COMMAND NOT FOUND**\nA command with the trigger `%s` was not found. To view this server's commands, use `@MoBot#0697 commands`.\n---" % trigger
    await message.channel.send(embed=embed)
    return
  else:
    embed = embed.to_dict()
    embed["author"]["url"] = embed["author"]["url"].replace("command_id=None", "command_id=%s" % command.command_id)
    embed = discord.Embed().from_dict(embed)

  embed.description = "---\n**Are you editing the trigger or the response?**\n\n__To update the trigger:__\n1. Type the new trigger\n2. Click the %s\n\n__To update the response:__\n1. Type the new response\n2. Click the %s\n\n__To reference a message:__\n1. Paste message ID\n2. Click the %s\n3. Click the %s\n*If you are referencing a message, then if the message is deleted or changed, the response will be affected.*\n---" % (ONE_EMOJI, TWO_EMOJI, NUMBER_SIGN_EMOJI, TWO_EMOJI)
  embed.add_field(name="__**Trigger**__", value="%s" % trigger)
  embed.add_field(name="__**Response**__", value="%s" % (command.response[:40] + ("..." if len(command.response) >= 40 else "")))
  embed.add_field(name="__**Other Details**__", value="Referencing Message: %s" % (command.referencingMessage))
  embed.set_footer(text="%s - Save Command %s - Full Response " % (FLOPPY_DISK_EMOJI, MAG_EMOJI))

  msg = await message.channel.send(embed=embed)
  await msg.add_reaction(ONE_EMOJI)
  await msg.add_reaction(TWO_EMOJI)
  await msg.add_reaction(NUMBER_SIGN_EMOJI)
  await msg.add_reaction(FLOPPY_DISK_EMOJI)
  await msg.add_reaction(MAG_EMOJI)
# end editCommandSession

async def createCommandSession(message, client):
  embed = discord.Embed(color=int("0xd1d1d1", 16))
  embed.set_author(name="MoBot Custom Commands", icon_url=client.user.avatar_url, url="https://google.com/SimpleCommands/command_id=None/guild_id=%s/command_owner_id=%s" % (message.guild.id, message.author.id))

  embed.description = "---\n**Follow the instructions below.**\n\nTo set your command, you will need to set a trigger and a response.\n\n__To update the trigger:__\n1. Type the new trigger\n2. Click the %s\n\n__To update the response:__\n1. Type the new response\n2. Click the %s\n3. Click the %s\n\n__To reference a message:__\n1. Paste message ID\n2. Click the %s\n3. Click the %s\n*If you are referencing a message, then if the message is deleted or changed, the response will be affected.*\n---" % (ONE_EMOJI, TWO_EMOJI, NUMBER_SIGN_EMOJI, TWO_EMOJI)

  embed.add_field(name="__**Trigger**__", value=spaceChar)
  embed.add_field(name="__**Response**__", value=spaceChar)
  embed.add_field(name="__**Other Details**__", value=spaceChar)
  embed.set_footer(text="%s - Save Command %s - Full Response " % (FLOPPY_DISK_EMOJI, MAG_EMOJI))

  msg = await message.channel.send(embed=embed)
  await msg.add_reaction(ONE_EMOJI)
  await msg.add_reaction(TWO_EMOJI)
  await msg.add_reaction(FLOPPY_DISK_EMOJI)
  await msg.add_reaction(MAG_EMOJI)
# end createCommandSession

async def handleNewTrigger(commandOwner, message, embed):
  history = await message.channel.history(after=message).flatten()
  trigger = None
  for msg in history:
    if (msg.author == commandOwner):
      trigger = msg.content

  oldTrigger = embed.fields[0].value[1:-3]
  if (trigger != oldTrigger):
    if (not triggerExists(trigger, getGuildCommands(message.guild.id))):
      embed.description = "---".join(embed.description.split("---")[:-1]) + "---"
      embed = embed.to_dict()
      embed["fields"][0]["value"] = trigger
      embed = discord.Embed().from_dict(embed)
    else:
      await message.channel.send("**Trigger Already Exists**\nEither edit/delete the other command, or use a different trigger for this command.", delete_after=10)
    await message.edit(embed=embed)
# end handleNewTrigger

async def handleNewResponse(commandOwner, message, embed):
  reactions = message.reactions
  referencingMessage = 0
  for reaction in reactions:
    if (reaction.emoji == NUMBER_SIGN_EMOJI):
      async for user in reaction.users():
        if (user.id == commandOwner.id):
          referencingMessage = 1
          await message.remove_reaction(reaction, commandOwner)
          break
      break

  history = await message.channel.history(after=message).flatten()
  response = None
  for msg in history:
    if (msg.author == commandOwner):
      response = msg.content

  command = getCommand(embed.fields[0].value, message.guild.id)
  try:
    oldResponse = command.response
  except AttributeError: # when commmand == None
    oldResponse = None  
  if (response != oldResponse and response is not None):
    if (referencingMessage == 1):
      m = await message.channel.send("**Searching for Message**\nThis could take a second or two, so don't click anything!")
      msg = None
      for channel in message.guild.text_channels:
        try:
          msg = await channel.fetch_message(int(response))
          break
        except discord.errors.NotFound:
          pass
        
      await m.delete()
      if (msg is None):
        await message.channel.send("**Message does not exist or <@%s> does not have access to the channel.**" % moBot, delete_after=10)
        return

    embed.description = "---".join(embed.description.split("---")[:-1]) + "---"
    embed = embed.to_dict()
    embed["fields"][1]["value"] = response[:40] + ("..." if len(response) >= 40 else "")
    embed = discord.Embed().from_dict(embed)
    embed = buildOtherDetails(embed, "Yes" if referencingMessage == 1 else "No", "Referencing Message: ")
    await message.edit(embed=embed)
# end handleNewResponse

async def saveCommand(message, embed):
  trigger = embed.fields[0].value
  response = embed.fields[1].value
  otherDetails = embed.fields[2].value
  print(otherDetails.split("Referencing Message:")[1].split("\n")[0].strip())
  referencingMessage = 1 if otherDetails.split("Referencing Message:")[1].split("\n")[0].strip() == "Yes" else 0
  print(referencingMessage)
  guild = message.guild
  owner = guild.get_member(int(embed.author.url.split("owner_id=")[1].split("/")[0]))
  command_id = embed.author.url.split("command_id=")[1].split("/")[0]

  if (spaceChar in trigger + response):
    return

  moBotDB = MoBotDatabase.connectDatabase()
  moBotDB.connection.commit()
  if (not triggerExists(trigger, getGuildCommands(message.guild.id))):  
    moBotDB.cursor.execute("""
    INSERT INTO `MoBot`.`custom_commands` 
      (`trigger`, `response`, `guild_name`, `guild_id`, `owner_name`, `owner_id`, referencing_message)      
    VALUES 
      ('%s', '%s', '%s', '%s', '%s', '%s', '%s');
    """ % (trigger.replace("'", "''"), response.replace("'", "''"), owner, owner.id, guild.name.replace("'", "''"), guild.id, referencingMessage))

  else:
    moBotDB.cursor.execute("""
    UPDATE custom_commands
    SET
      custom_commands.response = '%s',
      custom_commands.owner_name = '%s',
      custom_commands.owner_id = '%s',
      custom_commands.guild_name = '%s',
      custom_commands.referencing_message = '%s'
    WHERE
      custom_commands.command_id = %s""" % (response.replace("'", "''"), owner, owner.id, guild.name.replace("'", "''"), referencingMessage, command_id))

  moBotDB.connection.commit()
  moBotDB.connection.close()
  await message.channel.send("**Command Saved**", delete_after=2)
# end saveCommand

def buildOtherDetails(embed, detail, detailType):
  embed = embed.to_dict()
  otherDetails = embed["fields"][2]["value"]
  newOtherDetails = ""
  for line in otherDetails.split("\n"):
    if detailType not in line:
      newOtherDetails += line + "\n"
    else:
      newOtherDetails += detailType + detail + "\n"
  embed["fields"][2]["value"] = newOtherDetails
  return discord.Embed().from_dict(embed)
# end buildOtherDetails

def triggerExists(trigger, commandList): # checking guild commands if trigger matches
  command = [command for command in commandList if command.trigger == trigger]
  return None if not command else command[0]
# end triggerExists

def getGuildCommands(guildID):
  moBotDB = MoBotDatabase.connectDatabase()
  moBotDB.connection.commit()
  moBotDB.cursor.execute("""SELECT * FROM custom_commands 
    WHERE custom_commands.guild_id = %s""" % guildID)
  commandList = []
  for record in moBotDB.cursor:
    commandList.append(Command(record[0], record[1], record[2], record[3]))
  moBotDB.connection.close()
  return commandList
# end getGuildCommands

def getCommand(trigger, guildID):
  moBotDB = MoBotDatabase.connectDatabase()
  moBotDB.connection.commit()
  moBotDB.cursor.execute("""
    SELECT 
      custom_commands.command_id, custom_commands.trigger, custom_commands.response, custom_commands.referencing_message
    FROM custom_commands
    WHERE 
      custom_commands.guild_id = '%s' AND 
      custom_commands.trigger = '%s'
  """ % (guildID, trigger.replace("'", "''")))

  command = None
  for record in moBotDB.cursor:
    command = Command(record[0], record[1], record[2], record[3])
    break

  moBotDB.connection.close()
  return command
# end getCommand
